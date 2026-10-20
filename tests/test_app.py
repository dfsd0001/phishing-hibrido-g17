"""Pruebas de la interfaz Streamlit y de su cliente de la API.

La API se sustituye por un transporte simulado de httpx (cliente) o por funciones simuladas
(interfaz), de modo que las pruebas no necesitan modelos ni red.
"""

import base64
import copy
import json
import re
import sys

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from src.ioc_utils import iocs_vivos, urls_para_features
from src.url_features import descomponer
from tests.simulados import RAIZ

CARPETA_APP = RAIZ / "app"
sys.path.insert(0, str(CARPETA_APP))

import cliente_api  # noqa: E402
import contenido  # noqa: E402

RESPUESTA = json.loads((RAIZ / "contracts" / "golden" / "phishing.json").read_text(encoding="utf-8"))
CONFIG = cliente_api.Configuracion(url="http://api.test", clave="clave-prueba", timeout=5)


def transporte(estado: int = 200, cuerpo=None, excepcion: Exception | None = None):
    def responder(solicitud: httpx.Request) -> httpx.Response:
        if excepcion is not None:
            raise excepcion
        assert solicitud.headers["X-API-Key"] == "clave-prueba"
        return httpx.Response(estado, json=RESPUESTA if cuerpo is None else cuerpo)

    return httpx.MockTransport(responder)


# Cliente de la API


def test_analisis_correcto_devuelve_el_contrato():
    salida = cliente_api.analizar("Asunto", "Cuerpo", configuracion=CONFIG, transporte=transporte())
    assert salida["clasificacion"]["clase"] == "phishing"


def test_eml_se_envia_en_base64():
    enviado = {}

    def responder(solicitud):
        enviado.update(json.loads(solicitud.content))
        return httpx.Response(200, json=RESPUESTA)

    simulado = httpx.MockTransport(responder)
    cliente_api.analizar(eml=b"Subject: hola\n\ncuerpo", configuracion=CONFIG, transporte=simulado)
    assert base64.b64decode(enviado["eml_base64"]) == b"Subject: hola\n\ncuerpo"
    assert "cuerpo" not in enviado


@pytest.mark.parametrize(
    ("estado", "codigo"),
    [(401, "clave_invalida"), (422, "entrada_invalida"), (503, "modelo_no_disponible"), (500, "error_servidor")],
)
def test_codigos_http_se_traducen(estado, codigo):
    with pytest.raises(cliente_api.ErrorAPI) as error:
        cliente_api.analizar("a", "b", configuracion=CONFIG, transporte=transporte(estado, {"detail": "x"}))
    assert error.value.codigo == codigo


@pytest.mark.parametrize(
    ("excepcion", "codigo"),
    [(httpx.ConnectError("sin red"), "sin_conexion"), (httpx.ReadTimeout("lento"), "tiempo_agotado")],
)
def test_fallos_de_red(excepcion, codigo):
    with pytest.raises(cliente_api.ErrorAPI) as error:
        cliente_api.analizar("a", "b", configuracion=CONFIG, transporte=transporte(excepcion=excepcion))
    assert error.value.codigo == codigo


def test_respuesta_fuera_de_contrato():
    with pytest.raises(cliente_api.ErrorAPI) as error:
        cliente_api.analizar("a", "b", configuracion=CONFIG, transporte=transporte(cuerpo={"otra": 1}))
    assert error.value.codigo == "respuesta_invalida"


def test_estado_del_servicio_sin_conexion_devuelve_none():
    caido = transporte(excepcion=httpx.ConnectError("sin red"))
    assert cliente_api.estado_servicio(CONFIG, transporte=caido) is None


@pytest.mark.parametrize(
    ("asunto", "cuerpo", "eml", "esperado"),
    [
        ("", "   ", None, ["vacio"]),
        ("x" * 1001, "texto", None, ["asunto_largo"]),
        ("", "x" * 500_001, None, ["cuerpo_largo"]),
        ("", "", b"x" * 1_500_001, ["eml_grande"]),
        ("Asunto", "", None, []),
        ("", "", b"Subject: a", []),
    ],
)
def test_validacion_de_entrada(asunto, cuerpo, eml, esperado):
    assert cliente_api.validar_entrada(asunto, cuerpo, eml) == esperado


# Contenido


def test_ejemplos_defangeados_y_con_dominios_reservados():
    """Los ejemplos no tienen IOC vivos y sus URL usan dominios reservados (RFC 2606 y 6761)."""
    reservados = (".test", ".example", "example.com", "example.org", "example.net")
    for ejemplo in contenido.EJEMPLOS.values():
        texto = ejemplo["asunto"] + " " + ejemplo["cuerpo"]
        assert iocs_vivos(texto) == []
        for url in urls_para_features(texto):
            assert descomponer(url)[0].endswith(reservados), url


def test_textos_completos_en_ambos_idiomas():
    assert set(contenido.TEXTOS["es"]) == set(contenido.TEXTOS["en"])
    marcadores = {idioma: sorted(re.findall(r"\{(\w+)", "".join(contenido.TEXTOS[idioma]["tabla_metricas"].values())))
                  for idioma in ("es", "en")}
    assert marcadores["es"] == marcadores["en"]


def test_metricas_coinciden_con_los_resultados():
    metricas = RAIZ / "results" / "metrics"
    evaluacion = json.loads((metricas / "evaluacion_final.json").read_text(encoding="utf-8"))
    operativo = evaluacion["metricas_ic95"]["Fusión V3, umbral operativo"]
    enron = json.loads((metricas / "fpr_enron_v1.json").read_text(encoding="utf-8"))["umbral_operativo_A"]
    kpi = json.loads((metricas / "kpi" / "kpi_resumen.json").read_text(encoding="utf-8"))
    esperado = {
        "f1_macro": operativo["F1 macro"][0],
        "recall_phishing": operativo["Recall phishing"][0],
        "precision_phishing": operativo["Precisión phishing"][0],
        "fpr_phishing": operativo["FPR phishing"][0],
        "fpr_enron_pct": enron["FPR_enron_B_pct"],
        "recall_espanol": evaluacion["ruta_espanola"]["total"]["recall_phishing"],
        "fpr_espanol": evaluacion["ruta_espanola"]["total"]["fpr"],
        "latencia_p95_ms": kpi["latencia_ms_p95"],
    }
    for clave, valor in esperado.items():
        assert contenido.METRICAS[clave] == pytest.approx(valor, abs=5e-5), clave


# Interfaz


@pytest.fixture
def interfaz(monkeypatch):
    monkeypatch.setattr(cliente_api, "estado_servicio", lambda *a, **k: {"estado": "ok", "modelo": "fusion_v1",
                                                                            "variante": "V3", "version_api": "1.1",
                                                                            "umbral_en": 0.8586})
    prueba = AppTest.from_file(str(CARPETA_APP / "app.py"), default_timeout=30)
    return prueba


def textos_mostrados(prueba) -> str:
    partes = [e.value for e in prueba.markdown] + [e.value for e in prueba.error] + [e.value for e in prueba.warning]
    return "\n".join(str(p) for p in partes)


def test_la_interfaz_carga_sin_errores(interfaz):
    interfaz.run()
    assert not interfaz.exception
    assert interfaz.title[0].value == "Detector híbrido de phishing"
    etiquetas = [p.label for p in interfaz.tabs]
    for pestana in ("Analizar", "Historial", "Acerca del modelo", "Ayuda", "Pegar el texto", "Subir un archivo .eml"):
        assert pestana in etiquetas


def test_analizar_sin_datos_muestra_error(interfaz):
    interfaz.run()
    interfaz.button[1].click().run()
    assert any("Escriba el asunto" in e.value for e in interfaz.error)


def test_ejemplo_y_resultado(interfaz, monkeypatch):
    llamadas = []

    def analizar_simulado(asunto, cuerpo, eml=None):
        llamadas.append((asunto, cuerpo))
        return copy.deepcopy(RESPUESTA)

    monkeypatch.setattr(cliente_api, "analizar", analizar_simulado)
    interfaz.run()
    interfaz.button[0].click().run()
    assert interfaz.text_input[0].value == contenido.EJEMPLOS["phishing_en"]["asunto"]
    interfaz.button[1].click().run()
    assert not interfaz.exception
    assert llamadas and llamadas[0][0] == contenido.EJEMPLOS["phishing_en"]["asunto"]
    assert "Phishing" in textos_mostrados(interfaz)
    assert len(interfaz.session_state["historial"]) == 1


def test_error_de_conexion_se_explica(interfaz, monkeypatch):
    def sin_conexion(*args, **kwargs):
        raise cliente_api.ErrorAPI("sin_conexion")

    monkeypatch.setattr(cliente_api, "analizar", sin_conexion)
    interfaz.run()
    interfaz.text_area[0].input("Hola equipo, adjunto el informe semanal.").run()
    interfaz.button[1].click().run()
    assert any("No se pudo conectar" in e.value for e in interfaz.error)
    assert interfaz.session_state["historial"] == []


def test_idioma_no_soportado_advierte(interfaz, monkeypatch):
    respuesta = copy.deepcopy(RESPUESTA)
    respuesta["advertencias"] = ["idioma_no_soportado"]
    respuesta["idioma_detectado"] = "fr"
    monkeypatch.setattr(cliente_api, "analizar", lambda *a, **k: respuesta)
    interfaz.run()
    interfaz.text_area[0].input("Bonjour, votre compte a été suspendu.").run()
    interfaz.button[1].click().run()
    assert any("Idioma no soportado" in w.value for w in interfaz.warning)


def test_cambio_a_ingles(interfaz):
    interfaz.run()
    interfaz.radio(key="idioma_interfaz").set_value("English").run()
    assert interfaz.title[0].value == "Hybrid phishing detector"
