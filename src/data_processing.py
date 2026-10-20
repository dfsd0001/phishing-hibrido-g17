"""Lectura de correos, normalización de texto, preparación del dataset y particiones.

La misma función ``texto_para_modelo`` se usa en entrenamiento y en inferencia, de modo
que el modelo de producción recibe exactamente la representación con la que se entrenó.
Las funciones de preparación (exclusiones, particiones y pliegues fuera de distribución)
reproducen las decisiones documentadas en ``config.yaml``. Ninguna función resuelve ni
visita URL.
"""

from __future__ import annotations

import email
import hashlib
import html
import re
from email import policy
from email.message import Message

import pandas as pd
from sklearn.model_selection import train_test_split

MARCADORES = {
    "url": "__url__",
    "ip": "__ip__",
    "email": "__email__",
    "anio": "__anio__",
    "dominio_propio": "__dominio_propio__",
}

# Términos que delatarían el corpus de origen si aparecieran en el texto de entrada.
# Se usan como sonda de fuga de etiqueta en la preparación de datos.
TERMINOS_FUGA = (
    "phishing",
    "honeypot",
    "pot",
    "nazario",
    "monkey",
    "enron",
    "spamassassin",
    "ceas",
    "nigerian",
)

_SCRIPT_STYLE = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_ETIQUETA = re.compile(r"(?s)<[^>]+>")
_ESPACIOS = re.compile(r"\s+")
_ANIO_FECHA = re.compile(r"\b(199[5-9]|20[0-2]\d)\b")

_URL_DEFANGEADA = re.compile(r"(?i)\b(?:hxxps?|fxp)\[://\][^\s<>\"']*|\bwww\[\.\][^\s<>\"']*")
_IP_DEFANGEADA = re.compile(r"\b\d{1,3}\[\.\]\d{1,3}\[\.\]\d{1,3}\[\.\]\d{1,3}\b")
# El dominio puede faltar o no tener punto ("phishing@pot", anonimización del honeypot).
_EMAIL = re.compile(r"[\w.+-]+@(?:[\w-]+(?:\.[\w-]+)*)?")
_RACHA_SIMBOLO = re.compile(r"([^\w\s])\1{3,}")
_RACHA_GUION_BAJO = re.compile(r"_{4,}")
_ANIO_TEXTO = re.compile(r"\b(?:19[89]\d|20[0-2]\d)\b")


def _decodificar(parte: Message) -> str:
    """Decodifica una parte MIME probando el charset declarado y luego latin-1."""
    try:
        return parte.get_content()
    except Exception:
        crudo = parte.get_payload(decode=True) or b""
        for codificacion in (parte.get_content_charset() or "utf-8", "latin-1"):
            try:
                return crudo.decode(codificacion)
            except (LookupError, UnicodeDecodeError):
                continue
        return crudo.decode("utf-8", errors="replace")


def texto_de_email(crudo: bytes | Message) -> dict:
    """Extrae asunto, cuerpo, fecha declarada y tipos MIME de un correo en formato RFC 822.

    El cuerpo concatena las partes ``text/plain`` y ``text/html`` sin quitar etiquetas, para
    no perder los enlaces de los atributos ``href``. Los adjuntos se ignoran.
    """
    if isinstance(crudo, (bytes, bytearray)):
        mensaje = email.message_from_bytes(crudo, policy=policy.default)
    else:
        mensaje = email.message_from_bytes(crudo.as_bytes(), policy=policy.default)
    partes, tipos = [], []
    for parte in mensaje.walk() if mensaje.is_multipart() else [mensaje]:
        tipo = parte.get_content_type()
        tipos.append(tipo)
        if tipo in ("text/plain", "text/html") and parte.get_content_disposition() != "attachment":
            partes.append(_decodificar(parte))
    return {
        "subject": str(mensaje.get("Subject", "") or ""),
        "body": "\n".join(partes),
        "date": str(mensaje.get("Date", "") or ""),
        "mime": sorted(set(tipos)),
    }


def texto_plano(texto: str) -> str:
    """Quita bloques script/style y etiquetas HTML, decodifica entidades y colapsa espacios.

    Se usa para detectar el idioma, medir longitudes, deduplicar y como base del texto de
    los modelos. Para extraer URL debe usarse el texto original.
    """
    texto = _SCRIPT_STYLE.sub(" ", texto or "")
    texto = _ETIQUETA.sub(" ", texto)
    texto = html.unescape(texto)
    return _ESPACIOS.sub(" ", texto).strip()


def hash_normalizado(texto: str) -> str:
    """Huella SHA-1 para deduplicar: texto plano, minúsculas y espacios colapsados."""
    normalizado = texto_plano(texto).lower().encode("utf-8", "replace")
    return hashlib.sha1(normalizado).hexdigest()


def anio_de(fecha: str) -> int | None:
    """Año declarado en un encabezado Date (1995 a 2029), o ``None`` si no hay uno plausible."""
    coincidencia = _ANIO_FECHA.search(str(fecha or ""))
    return int(coincidencia.group(1)) if coincidencia else None


def texto_para_modelo(texto_defangeado: str, dominios_propios: tuple | list = ()) -> str:
    """Construye la entrada de TF-IDF y DistilBERT a partir de un texto ya defangeado.

    Transformaciones:

    * Quita HTML.
    * Sustituye URL, IPv4 y direcciones de correo por marcadores. Las URL las analiza la
      rama URL; así el texto no aprende dominios propios de cada corpus.
    * Enmascara años de 1980 a 2029, un confusor temporal detectado en el EDA.
    * Sustituye los ``dominios_propios`` por un marcador. En producción es el dominio de la
      organización: la señal útil es "el correo menciona tu dominio", no un buzón concreto.
    * Acorta rachas de símbolos repetidos.

    Args:
        texto_defangeado: Salida de ``ioc_utils.defang_texto``.
        dominios_propios: Dominios a enmascarar, por ejemplo ``("monkey.org", "monkey")``.
    """
    texto = texto_plano(texto_defangeado)
    texto = _URL_DEFANGEADA.sub(f" {MARCADORES['url']} ", texto)
    texto = _IP_DEFANGEADA.sub(f" {MARCADORES['ip']} ", texto)
    texto = _EMAIL.sub(f" {MARCADORES['email']} ", texto)
    texto = _ANIO_TEXTO.sub(f" {MARCADORES['anio']} ", texto)
    # El dominio más largo primero, para que "monkey.org" no quede como "__dominio_propio__.org".
    for dominio in sorted(dominios_propios, key=len, reverse=True):
        texto = re.sub(rf"(?i)\b{re.escape(dominio)}\b", f" {MARCADORES['dominio_propio']} ", texto)
    texto = _RACHA_SIMBOLO.sub(r"\1\1\1", texto)
    texto = _RACHA_GUION_BAJO.sub("___", texto)
    return _ESPACIOS.sub(" ", texto).strip()


# Orden en que se aplican las exclusiones. Cada correo recibe solo el primer motivo que cumple.
MOTIVOS_EXCLUSION = ("grupo_excluido", "casi_vacio", "idioma", "duplicado")


def marcar_exclusiones(correos: pd.DataFrame, reglas: dict) -> tuple[pd.DataFrame, dict]:
    """Asigna a cada correo su motivo de exclusión, o ``None`` si se conserva.

    El orden de las filas se fija antes de evaluar los duplicados (grupo, fuente y huella),
    de modo que el correo conservado de cada grupo de duplicados es siempre el mismo.

    Args:
        correos: Tabla intermedia con ``grupo``, ``fuente``, ``hash``, ``len_plano`` e ``idioma``.
        reglas: Sección ``preparacion`` de ``config.yaml``.

    Returns:
        La tabla ordenada con la columna ``motivo_exclusion`` y el número de correos
        excluidos por cada motivo.
    """
    tabla = correos.sort_values(["grupo", "fuente", "hash"], kind="stable").reset_index(drop=True)
    tabla["motivo_exclusion"] = None
    bitacora = {}

    def excluir(mascara: pd.Series, motivo: str) -> None:
        nuevos = mascara & tabla["motivo_exclusion"].isna()
        tabla.loc[nuevos, "motivo_exclusion"] = motivo
        bitacora[motivo] = int(nuevos.sum())

    excluir(tabla["grupo"].isin(reglas["grupos_excluidos"]), "grupo_excluido")
    excluir(tabla["len_plano"] < reglas["min_len_plano"], "casi_vacio")
    excluir(tabla["grupo"].isin(reglas["grupos_con_filtro_idioma"]) & (tabla["idioma"] != reglas["idioma"]), "idioma")
    vigentes = tabla["motivo_exclusion"].isna()
    repetidos = tabla[vigentes].duplicated("hash", keep="first").reindex(tabla.index, fill_value=False)
    excluir(vigentes & repetidos, "duplicado")
    return tabla, bitacora


def construir_dataset(tabla: pd.DataFrame, reglas: dict) -> pd.DataFrame:
    """Conserva los correos no excluidos y crea la clase numérica, el identificador y el texto de modelo.

    Raises:
        ValueError: Si los identificadores no son únicos o una clase queda con un solo corpus
            de origen (riesgo de que la clase sea un artefacto de la fuente).
    """
    datos = tabla[tabla["motivo_exclusion"].isna()].copy()
    datos["y"] = datos["clase"].map(reglas["clases"]).astype(int)
    dominios = reglas.get("dominios_propios", {})
    datos["texto_modelo"] = [
        texto_para_modelo(texto, tuple(dominios.get(grupo, ())))
        for texto, grupo in zip(datos["texto_defang"], datos["grupo"], strict=True)
    ]
    datos["id"] = datos["hash"].str[:16]
    if not datos["id"].is_unique:
        raise ValueError("Los identificadores derivados de la huella no son únicos")
    origenes = datos.groupby("clase")["grupo"].nunique()
    if origenes.min() < 2:
        raise ValueError(f"Una clase quedó con un solo corpus de origen: {origenes.to_dict()}")
    return datos


def particion_estratificada(datos: pd.DataFrame, proporciones: dict, semilla: int) -> pd.Series:
    """Partición entrenamiento, validación y prueba estratificada por clase y corpus de origen.

    Returns:
        Serie con ``train``, ``val`` o ``test`` alineada con el índice de ``datos``.
    """
    estrato = datos["clase"] + "|" + datos["grupo"]
    indices_train, indices_resto = train_test_split(
        datos.index, test_size=1 - proporciones["train"], stratify=estrato, random_state=semilla
    )
    fraccion_test = proporciones["test"] / (proporciones["val"] + proporciones["test"])
    indices_val, indices_test = train_test_split(
        indices_resto, test_size=fraccion_test, stratify=estrato.loc[indices_resto], random_state=semilla
    )
    particion = pd.Series("train", index=datos.index)
    particion.loc[indices_val] = "val"
    particion.loc[indices_test] = "test"
    return particion


def pliegues_fuera_de_distribucion(datos: pd.DataFrame, anio_corte: int) -> dict[str, pd.Series]:
    """Máscaras de los pliegues de evaluación fuera de distribución.

    * ``loso_<grupo>``: un corpus completo queda fuera del entrenamiento.
    * ``temporal_phishing_<anio>+``: el phishing desde ``anio_corte`` queda fuera.

    En cada pliegue, lo que cae en la máscara pasa completo a prueba y el resto conserva su
    partición (ver ``aplicar_pliegue``).
    """
    pliegues = {f"loso_{grupo}": datos["grupo"] == grupo for grupo in sorted(datos["grupo"].unique())}
    pliegues[f"temporal_phishing_{anio_corte}+"] = (datos["clase"] == "phishing") & (datos["anio"] >= anio_corte)
    return pliegues


def aplicar_pliegue(particion: pd.Series, fuera: pd.Series) -> pd.Series:
    """Envía a prueba todo lo que está fuera de distribución y deja el resto como estaba."""
    resultado = particion.copy()
    resultado[fuera] = "test"
    return resultado
