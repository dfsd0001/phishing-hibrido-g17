"""Pruebas del entrenamiento reproducible con un conjunto sintético pequeño."""

import json

import numpy as np
import pandas as pd
import pytest

from src import train
from src.ioc_utils import defang_url
from src.utils import cargar_config

FRASES = {
    0: "please review the attached quarterly report before the team meeting on monday",
    1: "special offer cheap watches discount buy now limited stock free shipping",
    2: "your account is suspended verify your password immediately or it will be closed",
}
# Dominios del TLD reservado .test (RFC 6761): uno distinto por correo, para que la
# separación de dominios entre particiones deje datos en todas ellas.
URLS = {
    0: "https://intranet{}.test/reports/q3",
    1: "http://shop{}.test/promo?id=1",
    2: "http://secure-login{}.test/verify/account/update?session=a1b2",
}


@pytest.fixture
def config():
    configuracion = cargar_config()
    configuracion["baseline"]["c_busqueda"] = [1.0]
    configuracion["baseline"]["palabras"]["min_df"] = 1
    configuracion["baseline"]["caracteres"]["min_df"] = 1
    configuracion["rama_url"]["xgboost"]["n_estimators"] = 30
    return configuracion


@pytest.fixture
def datos():
    generador = np.random.default_rng(0)
    filas = []
    for i in range(240):
        clase = i % 3
        particion = ["train"] * 6 + ["val"] * 2 + ["test"] * 2
        url = URLS[clase].format(i)
        filas.append(
            {
                "id": f"c{i}",
                "texto_modelo": f"{FRASES[clase]} ref {generador.integers(1000)}",
                "y": clase,
                "split": particion[i % 10],
                "urls_defang": [defang_url(url)],
            }
        )
    return pd.DataFrame(filas)


def test_baseline_elige_c_y_separa_las_clases(datos, config):
    modelo, resumen = train.entrenar_baseline(datos, config)
    assert resumen["c_optimo"] == 1.0
    assert resumen["busqueda"][1.0]["f1_macro_val"] > 0.9
    assert modelo.predict_proba(["verify your password now"]).shape == (1, 3)


def test_rama_url_con_dominios_disjuntos(datos, config):
    _, resumen = train.entrenar_url(datos, config)
    assert resumen["urls_entrenamiento"] > 0
    assert resumen["tld_categorias"][-1] == "__otro__"
    assert 0.0 <= resumen["auc_url_validacion"] <= 1.0


def test_rama_url_sin_columna_de_urls(datos, config):
    with pytest.raises(ValueError):
        train.entrenar_url(datos.drop(columns="urls_defang"), config)


def test_cli_guarda_artefacto_y_metadatos(datos, tmp_path):
    ruta_datos = tmp_path / "emails.parquet"
    datos.to_parquet(ruta_datos)
    salida = tmp_path / "modelos"
    assert train.main(["url", "--datos", str(ruta_datos), "--salida", str(salida)]) == 0
    metadatos = json.loads((salida / "url_xgb_correos.meta.json").read_text())
    assert metadatos["componente"] == "url"
    assert len(metadatos["sha256"]) == 64


def test_cli_informa_datos_inexistentes(tmp_path):
    assert train.main(["baseline", "--datos", str(tmp_path / "no_existe.parquet")]) == 1


def test_meta_calibrado_elige_calibracion_y_umbral_con_fpr_acotado():
    generador = np.random.default_rng(1)
    y = np.repeat([0, 1, 2], 200)
    X = generador.normal(size=(600, 3)) + np.eye(3)[y] * 2.5
    modelo, umbral, resumen = train.ajustar_meta_calibrado(X, y, semilla=17, fpr_max=0.01)
    assert resumen["calibracion"] in ("sigmoid", "isotonic")
    assert resumen["brier_val_cv"] == min(resumen["brier_por_calibracion"].values())
    assert resumen["val_cv"]["fpr_phishing"] <= 0.01
    assert 0.0 <= umbral <= 1.0
    assert modelo.predict_proba(X[:5]).shape == (5, 3)
