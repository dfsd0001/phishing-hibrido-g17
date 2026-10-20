"""Detector de producción: fusión tardía de las ramas de texto y URL.

Flujo de un correo:

1. Se defanga el texto y se construye la entrada de los modelos de lenguaje.
2. Se detecta el idioma. Inglés va por la ruta ``en_v3``; español, si el modelo multilingüe
   está disponible, por ``es_v1``; cualquier otro idioma recibe la advertencia
   ``idioma_no_soportado`` y debe revisarse manualmente.
3. Ruta inglesa (variante V3): log-probabilidades de DistilBERT y de la línea base TF-IDF,
   más el bloque de la rama URL, entran a un meta-clasificador calibrado.
4. Ruta española (V1_es): DistilBERT multilingüe y un meta-clasificador binario calibrado,
   sin rama URL, porque esa rama no transfiere al español (decisión D21).
5. La salida cumple el contrato JSON v1.2 y nunca contiene IOC vivos.

Las URL se refangan solo en memoria para calcular variables. ``torch`` se importa de forma
perezosa, de modo que las pruebas pueden usar componentes simulados sin GPU.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import math
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from . import data_processing as dp
from . import ioc_utils as ioc
from . import url_features as uf

log = logging.getLogger(__name__)

VERSION_CONTRATO = "1.2"
IDIOMAS_SOPORTADOS = {"en", "es"}
MIN_CHARS_IDIOMA = 40
CLASES = ["legitimo", "spam", "phishing"]
PH = 2
MAX_URLS = 20
MAX_CHARS_BASELINE = 5000
MAX_LEN_DISTILBERT = 256


def _log_prob(probabilidades: np.ndarray) -> np.ndarray:
    return np.log(np.clip(probabilidades, 1e-6, 1.0))


def _valor_o_neutro(valor: float | None) -> float:
    """Valor neutro 0,5 para correos sin URL (indicador ``sin_url`` en el bloque URL)."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return 0.5
    return valor


def features_meta(
    variante: str,
    p_distilbert: np.ndarray,
    p_baseline: np.ndarray,
    url_max: float | None,
    url_media: float | None,
    n_urls: int,
) -> np.ndarray:
    """Vector de entrada del meta-clasificador, idéntico al usado en el entrenamiento.

    Variantes: V0 (solo línea base), V1 (solo DistilBERT), V2 (DistilBERT + URL) y
    V3 (DistilBERT + línea base + URL). El bloque URL contiene el puntaje máximo, el medio,
    el indicador ``sin_url`` y ``log1p`` del número de URL.
    """
    bloque_url = np.array(
        [[_valor_o_neutro(url_max), _valor_o_neutro(url_media), float(n_urls == 0), math.log1p(n_urls)]]
    )
    variantes = {
        "V0": lambda: _log_prob(p_baseline),
        "V1": lambda: _log_prob(p_distilbert),
        "V2": lambda: np.c_[_log_prob(p_distilbert), bloque_url],
        "V3": lambda: np.c_[_log_prob(p_distilbert), _log_prob(p_baseline), bloque_url],
    }
    return variantes[variante]()


def matriz_meta(
    variante: str,
    p_distilbert: np.ndarray,
    p_baseline: np.ndarray,
    ramas_url: pd.DataFrame,
) -> np.ndarray:
    """Versión por lotes de ``features_meta`` para entrenar y evaluar el meta-clasificador.

    Args:
        p_distilbert: Probabilidades (n, 3) de DistilBERT.
        p_baseline: Probabilidades (n, 3) de la línea base.
        ramas_url: Tabla alineada con columnas ``url_b_max``, ``url_b_media`` y
            ``n_urls_eval``; los valores faltantes indican correos sin URL.
    """
    n_urls = ramas_url["n_urls_eval"].fillna(0).to_numpy(dtype=float)
    bloque_url = np.c_[
        ramas_url["url_b_max"].fillna(0.5).to_numpy(dtype=float),
        ramas_url["url_b_media"].fillna(0.5).to_numpy(dtype=float),
        (n_urls == 0).astype(float),
        np.log1p(n_urls),
    ]
    variantes = {
        "V0": lambda: _log_prob(p_baseline),
        "V1": lambda: _log_prob(p_distilbert),
        "V2": lambda: np.c_[_log_prob(p_distilbert), bloque_url],
        "V3": lambda: np.c_[_log_prob(p_distilbert), _log_prob(p_baseline), bloque_url],
    }
    return variantes[variante]()


def detectar_idioma(texto_plano: str) -> str:
    """Código ISO 639-1 detectado con langdetect (semilla fija), o ``indeterminado``."""
    muestra = texto_plano[:1000]
    if len(muestra) < MIN_CHARS_IDIOMA:
        return "indeterminado"
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0
        return detect(muestra)
    except Exception:
        return "indeterminado"


def nivel_riesgo(riesgo: int, es_phishing: bool) -> str:
    """Banda de riesgo para el SOC. Bandas provisionales, a validar con analistas."""
    if riesgo >= 90:
        return "critico"
    if es_phishing:
        return "alto"
    return "medio" if riesgo >= 10 else "bajo"


class Detector:
    """Clasificador de correos en legítimo, spam o phishing con puntaje de riesgo 0 a 100.

    Args:
        texto_fn: Función que recibe el texto de modelo y devuelve P(3) de DistilBERT.
        baseline: Pipeline TF-IDF + regresión logística con ``predict_proba``.
        url_modelo: Clasificador XGBoost de la rama URL.
        tld_categorias: Categorías de TLD vistas en el entrenamiento de la rama URL.
        meta: Meta-clasificador calibrado de la ruta inglesa.
        umbral: Umbral sobre P(phishing) de la ruta inglesa.
        variante: Variante de fusión (``V0`` a ``V3``).
        dominios_propios: Dominios de la organización que se enmascaran en el texto.
        version_modelo: Identificador de la versión publicada.
        es: Componentes de la ruta española (``texto_fn``, ``meta``, ``umbral``, ``variante``).
    """

    def __init__(
        self,
        texto_fn: Callable[[str], np.ndarray],
        baseline,
        url_modelo,
        tld_categorias,
        meta,
        umbral: float,
        variante: str,
        dominios_propios=(),
        version_modelo: str = "fusion_v1",
        es: dict | None = None,
    ):
        self.texto_fn = texto_fn
        self.baseline = baseline
        self.url_modelo = url_modelo
        self.tld_categorias = list(tld_categorias)
        self.meta = meta
        self.umbral = float(umbral)
        self.variante = variante
        self.dominios_propios = tuple(dominios_propios)
        self.version_modelo = version_modelo
        self.es = es

    @classmethod
    def desde_directorio(
        cls,
        base: str | Path,
        dominios_propios=(),
        dispositivo: str = "cpu",
        umbral_en: float | None = None,
    ) -> Detector:
        """Carga los artefactos publicados desde ``<base>/models``.

        Args:
            base: Carpeta que contiene ``models/`` (descarga del Hub o carpeta del proyecto).
            dominios_propios: Dominios de la organización.
            dispositivo: ``cpu`` o ``cuda``.
            umbral_en: Umbral operativo de la ruta inglesa (decisión D27). Si es ``None`` se
                usa el umbral de validación (FPR <= 1 %, decisión D9).
        """
        import joblib
        import xgboost as xgb

        modelos = Path(base) / "models"
        fusion = joblib.load(modelos / "fusion_v1.joblib")
        url_modelo = xgb.XGBClassifier()
        url_modelo.load_model(modelos / "url_xgb_v1b_correos.json")
        tld = json.loads((modelos / "url_xgb_v1.meta.json").read_text())["tld_categorias"]

        es = None
        if (modelos / "distilbert_multi_v1").exists() and (modelos / "fusion_es_v1.joblib").exists():
            fusion_es = joblib.load(modelos / "fusion_es_v1.joblib")
            es = {
                "texto_fn": _distilbert_fn(modelos / "distilbert_multi_v1", dispositivo),
                "meta": fusion_es["modelo"],
                "umbral": float(fusion_es["umbral_fpr1"]),
                "variante": fusion_es["variante"],
            }
        umbral = fusion["umbral_fpr1"] if umbral_en is None else float(umbral_en)
        log.info("Detector cargado: variante %s, umbral inglés %.4f", fusion["variante"], umbral)
        return cls(
            _distilbert_fn(modelos / "distilbert_v1", dispositivo),
            joblib.load(modelos / "baseline_tfidf_lr_v1.joblib"),
            url_modelo,
            tld,
            fusion["modelo"],
            umbral,
            fusion["variante"],
            dominios_propios,
            es=es,
        )

    def _rama_url(self, texto: str) -> tuple[float | None, float | None, int]:
        """Puntaje máximo y medio de las URL del correo. Las URL vivas no salen de esta función."""
        urls = ioc.urls_para_features(texto)[:MAX_URLS]
        if not urls:
            return None, None, 0
        variables = pd.DataFrame([uf.features_url(u) for u in urls])
        del urls
        X = variables[uf.NUMERICAS].astype(float).copy()
        tld = variables["tld"].where(variables["tld"].isin(self.tld_categorias), "__otro__")
        X["tld"] = pd.Categorical(tld, categories=self.tld_categorias)
        puntajes = self.url_modelo.predict_proba(X)[:, 1]
        return float(puntajes.max()), float(puntajes.mean()), int(len(puntajes))

    def _ruta_espanol(self, texto_modelo, url_max, url_media, n_urls):
        p_texto = np.asarray(self.es["texto_fn"](texto_modelo), dtype=float).reshape(1, 3)
        if self.es["variante"] == "V1_es":
            X = _log_prob(p_texto)
        else:
            bloque = [[_valor_o_neutro(url_max), _valor_o_neutro(url_media), float(n_urls == 0), math.log1p(n_urls)]]
            X = np.c_[_log_prob(p_texto), bloque]
        p_phishing = float(self.es["meta"].predict_proba(X)[0, 1])
        # Legítimo frente a spam lo decide el texto; el meta-clasificador es binario.
        resto = p_texto[0, :2] / max(p_texto[0, :2].sum(), 1e-9)
        probabilidades = np.array([(1 - p_phishing) * resto[0], (1 - p_phishing) * resto[1], p_phishing])
        clase = PH if p_phishing >= self.es["umbral"] else int(np.argmax(resto))
        return probabilidades, clase, p_texto, None

    def _ruta_ingles(self, texto_modelo, url_max, url_media, n_urls):
        p_texto = np.asarray(self.texto_fn(texto_modelo), dtype=float).reshape(1, 3)
        p_base = self.baseline.predict_proba([texto_modelo[:MAX_CHARS_BASELINE]])
        p_base = np.asarray(p_base, dtype=float).reshape(1, 3)
        X = features_meta(self.variante, p_texto, p_base, url_max, url_media, n_urls)
        probabilidades = self.meta.predict_proba(X)[0]
        if probabilidades[PH] >= self.umbral:
            clase = PH
        else:
            clase = int(np.argmax(probabilidades[:2]))
        return probabilidades, clase, p_texto, p_base

    def analizar(self, asunto: str = "", cuerpo: str = "", crudo: bytes | None = None) -> dict:
        """Analiza un correo y devuelve un diccionario conforme al contrato JSON v1.2.

        Args:
            asunto: Asunto del correo.
            cuerpo: Cuerpo en texto o HTML.
            crudo: Correo completo en formato RFC 822. Si se entrega, reemplaza a asunto y cuerpo.

        Raises:
            RuntimeError: Si la salida contuviera un IOC vivo (última barrera de seguridad).
        """
        inicio = time.perf_counter()
        if crudo is not None:
            partes = dp.texto_de_email(crudo)
            asunto, cuerpo = partes["subject"], partes["body"]
            huella = hashlib.sha256(crudo).hexdigest()
        else:
            huella = hashlib.sha256((asunto + "\n" + cuerpo).encode("utf-8", "replace")).hexdigest()

        texto = f"{asunto}\n{cuerpo}"
        texto_modelo = dp.texto_para_modelo(ioc.defang_texto(texto), self.dominios_propios)
        idioma = detectar_idioma(dp.texto_plano(texto))
        url_max, url_media, n_urls = self._rama_url(texto)

        if idioma == "es" and self.es is not None:
            ruta, variante, umbral = "es_v1", self.es["variante"], self.es["umbral"]
            probabilidades, clase, p_texto, p_base = self._ruta_espanol(texto_modelo, url_max, url_media, n_urls)
        else:
            ruta, variante, umbral = "en_v3", self.variante, self.umbral
            probabilidades, clase, p_texto, p_base = self._ruta_ingles(texto_modelo, url_max, url_media, n_urls)

        riesgo = int(round(100 * float(probabilidades[PH])))
        iocs = ioc.extraer_iocs(texto)
        es_phishing = clase == PH
        soportado = idioma in ("indeterminado", "en") or (idioma == "es" and self.es is not None)
        mitre = []
        if es_phishing:
            mitre.append({"tecnica": "T1566", "nombre": "Phishing"})
            if iocs["n_urls"] > 0:
                mitre.append({"tecnica": "T1566.002", "nombre": "Spearphishing Link"})

        def _redondear(p):
            return {c: round(float(v), 6) for c, v in zip(CLASES, p, strict=True)}

        salida = {
            "version_contrato": VERSION_CONTRATO,
            "id_analisis": str(uuid.uuid4()),
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "modelo": {"version": self.version_modelo, "variante": variante, "umbral_phishing": round(umbral, 6)},
            "ruta_modelo": ruta,
            "correo": {"sha256": huella, "asunto_defang": ioc.defang_texto(asunto)[:300]},
            "clasificacion": {
                "clase": CLASES[clase],
                "riesgo": riesgo,
                "nivel_riesgo": nivel_riesgo(riesgo, es_phishing),
                "probabilidades": _redondear(probabilidades),
            },
            "ramas": {
                "texto_distilbert": _redondear(p_texto[0]),
                "texto_baseline": None if p_base is None else _redondear(p_base[0]),
                "url": {
                    "max": None if url_max is None else round(url_max, 6),
                    "media": None if url_media is None else round(url_media, 6),
                    "n_urls": n_urls,
                    "sin_url": n_urls == 0,
                },
            },
            "iocs": {
                "urls": iocs["urls"],
                "ips": iocs["ips"],
                "n_urls": iocs["n_urls"],
                "n_ips": iocs["n_ips"],
            },
            "mitre_attack": mitre,
            "idioma_detectado": idioma,
            "advertencias": [] if soportado else ["idioma_no_soportado"],
            "latencia_ms": round(1000 * (time.perf_counter() - inicio), 1),
        }
        if ioc.iocs_vivos(json.dumps(salida, ensure_ascii=False)):
            raise RuntimeError("La salida contiene un IOC vivo; se bloquea la respuesta")
        return salida


def _distilbert_fn(ruta: Path, dispositivo: str = "cpu") -> Callable[[str], np.ndarray]:
    """Devuelve una función texto -> P(3) con un DistilBERT ajustado. Importa torch al usarse."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizador = AutoTokenizer.from_pretrained(ruta)
    modelo = AutoModelForSequenceClassification.from_pretrained(ruta).to(dispositivo).eval()

    def predecir(texto: str) -> np.ndarray:
        with torch.no_grad():
            entrada = tokenizador(texto, truncation=True, max_length=MAX_LEN_DISTILBERT, return_tensors="pt").to(
                dispositivo
            )
            return torch.softmax(modelo(**entrada).logits.float(), -1).cpu().numpy()[0]

    return predecir
