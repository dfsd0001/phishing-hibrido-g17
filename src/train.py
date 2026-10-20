"""Entrenamiento reproducible de los componentes que no requieren GPU.

Componentes:

* ``baseline``: TF-IDF de palabras y caracteres con regresión logística; el parámetro C se
  elige por F1 macro en validación.
* ``url``: XGBoost sobre las variables léxicas de las URL de los correos. Cada URL hereda la
  clase de su correo (etiqueta débil) y ningún dominio de validación o prueba entra al
  entrenamiento (variante B, dominios disjuntos), para no medir memoria de dominios.
* Meta-clasificador de la fusión (``ajustar_meta_calibrado``): se ajusta sobre validación a
  partir de las salidas de las ramas; lo usan ``notebooks/03_modelado.ipynb`` y el notebook
  07 de experimentación.

DistilBERT se ajusta en GPU con los notebooks 06 y 11 de ``notebooks/experimentos``,
porque su costo no es razonable en CPU.

Uso:
    python -m src.train baseline --datos data/processed/emails_v1.parquet --salida models
    python -m src.train url --datos data/processed/emails_v1.parquet --salida models
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline

from . import evaluate as ev
from . import ioc_utils as ioc
from . import url_features as uf
from .utils import cargar_config, configurar_logging, fijar_semillas

log = logging.getLogger(__name__)

COLUMNAS_REQUERIDAS = {"id", "texto_modelo", "y", "split"}


def construir_baseline(c: float, config: dict) -> Pipeline:
    """Pipeline TF-IDF (palabras y caracteres) más regresión logística balanceada."""
    p, k = config["baseline"]["palabras"], config["baseline"]["caracteres"]
    variables = FeatureUnion(
        [
            (
                "palabras",
                TfidfVectorizer(
                    ngram_range=tuple(p["ngram_range"]),
                    min_df=p["min_df"],
                    max_df=p["max_df"],
                    max_features=p["max_features"],
                    sublinear_tf=True,
                ),
            ),
            (
                "caracteres",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=tuple(k["ngram_range"]),
                    min_df=k["min_df"],
                    max_features=k["max_features"],
                    sublinear_tf=True,
                ),
            ),
        ]
    )
    clasificador = LogisticRegression(C=c, max_iter=config["baseline"]["max_iter"], class_weight="balanced")
    return Pipeline([("tfidf", variables), ("lr", clasificador)])


def entrenar_baseline(datos: pd.DataFrame, config: dict) -> tuple[Pipeline, dict]:
    """Elige C por F1 macro en validación y devuelve el modelo elegido con su resumen.

    El ajuste es determinista, así que se conserva el modelo de la búsqueda en lugar de
    reajustarlo; solo se guarda en memoria el mejor hasta el momento.
    """
    texto = datos["texto_modelo"].str[: config["texto"]["max_chars_baseline"]]
    train, val = (datos["split"] == "train").values, (datos["split"] == "val").values
    busqueda, mejor_modelo, mejor_f1 = {}, None, -1.0
    for c in config["baseline"]["c_busqueda"]:
        inicio = time.time()
        modelo = construir_baseline(c, config).fit(texto[train], datos.loc[train, "y"])
        f1_val = float(f1_score(datos.loc[val, "y"], modelo.predict(texto[val]), average="macro"))
        busqueda[c] = {"f1_macro_val": round(f1_val, 4), "segundos": round(time.time() - inicio, 1)}
        log.info("Baseline C=%s: F1 macro en validación %.4f", c, f1_val)
        if f1_val > mejor_f1:
            mejor_modelo, mejor_f1 = modelo, f1_val
    c_optimo = max(busqueda, key=lambda c: busqueda[c]["f1_macro_val"])
    return mejor_modelo, {"c_optimo": c_optimo, "busqueda": busqueda}


def tabla_urls(datos: pd.DataFrame, max_urls: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Una fila por URL de correo con sus variables léxicas, clase, partición y dominio.

    Las URL se refangan solo dentro de esta función y se descartan antes de devolver.
    """
    filas = []
    for id_correo, urls in zip(datos["id"], datos["urls_defang"], strict=True):
        for url in list(urls)[:max_urls]:
            filas.append((id_correo, ioc.refang(url)))
    urls = pd.DataFrame(filas, columns=["id", "url"])
    variables = pd.DataFrame([uf.features_url(u) for u in urls["url"]])
    hosts = [uf.descomponer(u)[0] for u in urls["url"]]
    urls = urls.drop(columns="url")
    urls["dominio"] = [".".join(h.split(".")[-2:]) for h in hosts]
    urls = urls.merge(datos[["id", "y", "split"]], on="id", how="left")
    urls["y"] = (urls["y"] == 2).astype(int)
    return urls, variables


def matriz_url(variables: pd.DataFrame, categorias_tld: list[str]) -> pd.DataFrame:
    """Matriz numérica de la rama URL con el TLD como variable categórica."""
    X = variables[uf.NUMERICAS].astype(float).copy()
    tld = variables["tld"].where(variables["tld"].isin(categorias_tld), "__otro__")
    X["tld"] = pd.Categorical(tld, categories=categorias_tld)
    return X


def entrenar_url(datos: pd.DataFrame, config: dict, categorias_tld: list[str] | None = None):
    """Entrena la rama URL con dominios disjuntos entre entrenamiento y evaluación.

    Args:
        categorias_tld: Lista fija de categorías. Si es ``None`` se toman los TLD más
            frecuentes del entrenamiento. El artefacto publicado (v1) usó la lista guardada en
            ``url_xgb_v1.meta.json``.
    """
    import xgboost as xgb

    if "urls_defang" not in datos.columns:
        raise ValueError("Los datos no tienen la columna 'urls_defang'")
    cfg = config["rama_url"]
    urls, variables = tabla_urls(datos, cfg["max_urls_por_correo"])
    dominios_evaluacion = set(urls.loc[urls["split"].isin(["val", "test"]), "dominio"])
    train = ((urls["split"] == "train") & ~urls["dominio"].isin(dominios_evaluacion)).values
    val = (urls["split"] == "val").values
    if urls.loc[train, "y"].nunique() < 2 or urls.loc[val, "y"].nunique() < 2:
        raise ValueError("Con dominios disjuntos, entrenamiento o validación quedó con una sola clase")
    if categorias_tld is None:
        frecuentes = variables.loc[train, "tld"].value_counts().head(cfg["top_tld"]).index.tolist()
        categorias_tld = frecuentes + ["__otro__"]
    X = matriz_url(variables, categorias_tld)
    modelo = xgb.XGBClassifier(
        **cfg["xgboost"],
        tree_method="hist",
        enable_categorical=True,
        eval_metric="aucpr",
        random_state=config["semilla"],
        n_jobs=-1,
    )
    modelo.fit(X[train], urls.loc[train, "y"], eval_set=[(X[val], urls.loc[val, "y"])], verbose=False)
    auc_val = roc_auc_score(urls.loc[val, "y"], modelo.predict_proba(X[val])[:, 1])
    log.info("Rama URL: %d URL de entrenamiento, AUC en validación %.4f", int(train.sum()), auc_val)
    resumen = {
        "urls_entrenamiento": int(train.sum()),
        "urls_descartadas_por_dominio": int(((urls["split"] == "train").values & ~train).sum()),
        "mejor_iteracion": int(modelo.best_iteration),
        "auc_url_validacion": round(float(auc_val), 4),
        "tld_categorias": categorias_tld,
    }
    return modelo, resumen


def meta_clasificador(metodo: str) -> CalibratedClassifierCV:
    """Regresión logística sobre las salidas de las ramas, calibrada con ``sigmoid`` o ``isotonic``."""
    return CalibratedClassifierCV(LogisticRegression(C=1.0, max_iter=3000), method=metodo, cv=5)


def ajustar_meta_calibrado(
    X_val: np.ndarray,
    y_val: np.ndarray,
    semilla: int,
    fpr_max: float = 0.01,
) -> tuple[CalibratedClassifierCV, float, dict]:
    """Ajusta el meta-clasificador de la fusión tardía sobre el conjunto de validación.

    Procedimiento (notebook 07):

    1. Probabilidades fuera de pliegue en validación (5 pliegues) para cada calibración.
    2. Se elige la calibración con menor puntaje de Brier.
    3. El umbral de phishing es el más bajo con FPR <= ``fpr_max`` sobre esas probabilidades.
    4. El modelo final se ajusta con toda la validación.

    Las ramas se entrenaron en ``train``, de modo que validación es un conjunto que ninguna
    rama vio. La prueba no interviene en ninguna decisión.

    Returns:
        Modelo ajustado, umbral y resumen con la calibración elegida y las métricas en
        validación cruzada.
    """
    pliegues = StratifiedKFold(5, shuffle=True, random_state=semilla)
    candidatos = {}
    for metodo in ("sigmoid", "isotonic"):
        p_cv = cross_val_predict(meta_clasificador(metodo), X_val, y_val, cv=pliegues, method="predict_proba")
        candidatos[metodo] = (ev.brier(y_val, p_cv), p_cv)
    metodo = min(candidatos, key=lambda m: candidatos[m][0])
    brier_cv, p_cv = candidatos[metodo]
    umbral = ev.umbral_por_fpr(y_val, p_cv[:, ev.PH], fpr_max)
    modelo = meta_clasificador(metodo).fit(X_val, y_val)
    resumen = {
        "calibracion": metodo,
        "brier_val_cv": brier_cv,
        "brier_por_calibracion": {m: v[0] for m, v in candidatos.items()},
        "umbral": umbral,
        "val_cv": ev.metricas(y_val, ev.predecir(p_cv, umbral)),
        "ece_phishing_val_cv": ev.ece_phishing(y_val, p_cv[:, ev.PH]),
    }
    return modelo, umbral, resumen


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_datos(ruta: Path) -> pd.DataFrame:
    """Lee el parquet procesado y valida sus columnas mínimas."""
    datos = pd.read_parquet(ruta)
    faltantes = COLUMNAS_REQUERIDAS - set(datos.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en {ruta}: {sorted(faltantes)}")
    return datos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Entrenamiento de la línea base y de la rama URL")
    parser.add_argument("componente", choices=["baseline", "url"])
    parser.add_argument("--datos", type=Path, required=True, help="Parquet procesado (emails_v1)")
    parser.add_argument("--salida", type=Path, default=Path("models"))
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--tld-meta", type=Path, default=None, help="JSON con 'tld_categorias' fijas")
    args = parser.parse_args(argv)

    configurar_logging()
    config = cargar_config(args.config)
    fijar_semillas(config["semilla"])
    try:
        datos = cargar_datos(args.datos)
    except (FileNotFoundError, ValueError) as error:
        log.error("No se pudieron cargar los datos: %s", error)
        return 1

    args.salida.mkdir(parents=True, exist_ok=True)
    inicio = time.time()
    if args.componente == "baseline":
        modelo, resumen = entrenar_baseline(datos, config)
        ruta = args.salida / "baseline_tfidf_lr.joblib"
        joblib.dump(modelo, ruta)
    else:
        categorias = None
        if args.tld_meta:
            categorias = json.loads(args.tld_meta.read_text())["tld_categorias"]
        try:
            modelo, resumen = entrenar_url(datos, config, categorias)
        except ValueError as error:
            log.error("No se pudo entrenar la rama URL: %s", error)
            return 1
        ruta = args.salida / "url_xgb_correos.json"
        modelo.save_model(ruta)

    resumen.update(
        {
            "componente": args.componente,
            "datos": args.datos.name,
            "n_correos": int(len(datos)),
            "semilla": config["semilla"],
            "segundos": round(time.time() - inicio, 1),
            "sha256": _sha256(ruta),
        }
    )
    ruta.with_suffix(".meta.json").write_text(json.dumps(resumen, indent=1, ensure_ascii=False))
    log.info("Artefacto guardado en %s", ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
