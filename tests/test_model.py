"""Pruebas del detector y del contrato JSON v1.2 con componentes simulados."""

import copy
import json

import jsonschema
import numpy as np
import pandas as pd
import pytest

from src.ioc_utils import iocs_vivos
from src.model import features_meta, matriz_meta, nivel_riesgo
from tests.simulados import CORREOS, RAIZ, VALIDADOR, detector_bilingue, detector_ingles

ESPANOL_LEGITIMO = (
    "Reunión de equipo",
    "Hola equipo, nos vemos el martes a las diez para revisar el informe trimestral del proyecto.",
)


@pytest.fixture(scope="module")
def detector():
    return detector_ingles()


@pytest.fixture(scope="module")
def detector_bi():
    return detector_bilingue()


@pytest.mark.parametrize("nombre", CORREOS)
def test_salida_cumple_el_contrato_y_no_tiene_iocs_vivos(detector, nombre):
    salida = detector.analizar(*CORREOS[nombre])
    VALIDADOR.validate(salida)
    assert iocs_vivos(json.dumps(salida)) == []


def test_phishing_con_url_se_mapea_a_t1566_002(detector):
    salida = detector.analizar(*CORREOS["phishing"])
    assert salida["clasificacion"]["clase"] == "phishing"
    assert [m["tecnica"] for m in salida["mitre_attack"]] == ["T1566", "T1566.002"]
    assert salida["iocs"]["urls"]
    assert salida["iocs"]["ips"] == ["192[.]0[.]2[.]4"]


def test_correo_sin_url_usa_valor_neutro(detector):
    salida = detector.analizar(*CORREOS["legitimo"])
    assert salida["ramas"]["url"] == {"max": None, "media": None, "n_urls": 0, "sin_url": True}
    assert salida["mitre_attack"] == []


def test_correo_crudo_eml(detector):
    crudo = (
        b"Subject: Verify now\r\nContent-Type: text/plain\r\n\r\n"
        b"Please verify your password at http://login.example.com/x\r\n"
    )
    salida = detector.analizar(crudo=crudo)
    VALIDADOR.validate(salida)
    assert salida["correo"]["asunto_defang"] == "Verify now"


def test_features_meta_coincide_con_el_entrenamiento():
    p_texto = np.array([[0.2, 0.3, 0.5]])
    p_base = np.array([[0.1, 0.1, 0.8]])
    X = features_meta("V3", p_texto, p_base, None, None, 0)
    assert X.shape == (1, 10)
    assert X[0, 6] == 0.5
    assert X[0, 8] == 1.0
    assert X[0, 9] == 0.0


def test_esquema_rechaza_una_url_viva(detector):
    salida = copy.deepcopy(detector.analizar(*CORREOS["phishing"]))
    salida["iocs"]["urls"] = ["https://evil.example.com"]
    with pytest.raises(jsonschema.ValidationError):
        VALIDADOR.validate(salida)


@pytest.mark.parametrize("archivo", sorted((RAIZ / "contracts" / "golden").glob("*.json")), ids=lambda p: p.name)
def test_archivos_de_referencia(archivo):
    texto = archivo.read_text(encoding="utf-8")
    VALIDADOR.validate(json.loads(texto))
    assert iocs_vivos(texto) == []


@pytest.mark.parametrize(
    ("riesgo", "es_phishing", "esperado"),
    [(95, True, "critico"), (70, True, "alto"), (40, False, "medio"), (5, False, "bajo")],
)
def test_bandas_de_riesgo(riesgo, es_phishing, esperado):
    assert nivel_riesgo(riesgo, es_phishing) == esperado


def test_espanol_sin_ruta_espanola_advierte(detector):
    salida = detector.analizar(*ESPANOL_LEGITIMO)
    VALIDADOR.validate(salida)
    assert salida["idioma_detectado"] == "es"
    assert salida["advertencias"] == ["idioma_no_soportado"]
    assert salida["ruta_modelo"] == "en_v3"


def test_ingles_sin_advertencia(detector):
    salida = detector.analizar(*CORREOS["phishing"])
    assert salida["idioma_detectado"] == "en"
    assert salida["advertencias"] == []


def test_texto_corto_queda_indeterminado(detector):
    salida = detector.analizar("", "ok gracias")
    assert salida["idioma_detectado"] == "indeterminado"
    assert salida["advertencias"] == []


def test_ruta_espanola_phishing(detector_bi):
    salida = detector_bi.analizar(
        "Cuenta bloqueada",
        "Estimado cliente, verifique su contraseña de inmediato en https://banco-seguro.example.com/login "
        "para evitar el cierre definitivo de su cuenta.",
    )
    VALIDADOR.validate(salida)
    assert salida["ruta_modelo"] == "es_v1"
    assert salida["advertencias"] == []
    assert salida["clasificacion"]["clase"] == "phishing"
    assert salida["ramas"]["texto_baseline"] is None
    assert salida["modelo"]["variante"] == "V1_es"
    assert abs(sum(salida["clasificacion"]["probabilidades"].values()) - 1) < 1e-6


def test_ruta_espanola_legitimo(detector_bi):
    salida = detector_bi.analizar(*ESPANOL_LEGITIMO)
    VALIDADOR.validate(salida)
    assert salida["ruta_modelo"] == "es_v1"
    assert salida["clasificacion"]["clase"] == "legitimo"


def test_ingles_sigue_en_la_ruta_v3(detector_bi):
    salida = detector_bi.analizar(*CORREOS["phishing"])
    VALIDADOR.validate(salida)
    assert salida["ruta_modelo"] == "en_v3"
    assert salida["ramas"]["texto_baseline"] is not None


def test_otro_idioma_advierte(detector_bi):
    salida = detector_bi.analizar(
        "Réunion",
        "Bonjour à tous, la réunion de l'équipe aura lieu mardi prochain à dix heures dans la grande salle.",
    )
    VALIDADOR.validate(salida)
    assert salida["advertencias"] == ["idioma_no_soportado"]
    assert salida["ruta_modelo"] == "en_v3"


def test_umbral_operativo_cambia_la_decision():
    """Un umbral inalcanzable (mayor que 1) impide clasificar como phishing; el riesgo no cambia."""
    detector = detector_ingles()
    antes = detector.analizar(*CORREOS["phishing"])["clasificacion"]
    detector.umbral = 1.01
    despues = detector.analizar(*CORREOS["phishing"])["clasificacion"]
    assert antes["clase"] == "phishing"
    assert despues["clase"] != "phishing"
    assert despues["riesgo"] == antes["riesgo"]


def test_matriz_meta_por_lotes_coincide_con_la_version_individual():
    generador = np.random.default_rng(0)
    p_texto = generador.dirichlet(np.ones(3), 4)
    p_base = generador.dirichlet(np.ones(3), 4)
    ramas = pd.DataFrame(
        {"url_b_max": [0.9, np.nan, 0.2, 0.7], "url_b_media": [0.5, np.nan, 0.1, 0.6], "n_urls_eval": [3, np.nan, 1, 0]}
    )
    lote = matriz_meta("V3", p_texto, p_base, ramas)
    for i, fila in ramas.iterrows():
        n = 0 if np.isnan(fila["n_urls_eval"]) else int(fila["n_urls_eval"])
        maximo = None if np.isnan(fila["url_b_max"]) else fila["url_b_max"]
        media = None if np.isnan(fila["url_b_media"]) else fila["url_b_media"]
        individual = features_meta("V3", p_texto[i : i + 1], p_base[i : i + 1], maximo, media, n)
        assert np.allclose(lote[i], individual[0])
