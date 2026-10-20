"""Pruebas del servicio FastAPI con el detector simulado (sin red ni GPU)."""

import base64

import pytest
from fastapi.testclient import TestClient

from api.app import crear_app
from tests.simulados import CORREOS, VALIDADOR, detector_ingles

CLAVE = "clave-de-prueba"
CABECERA = {"X-API-Key": CLAVE}


@pytest.fixture(scope="module")
def cliente():
    with TestClient(crear_app(detector=detector_ingles(), api_key=CLAVE)) as cliente_prueba:
        yield cliente_prueba


def test_salud(cliente):
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


def test_sin_clave_responde_401(cliente):
    assert cliente.post("/v1/analizar", json={"cuerpo": "hola"}).status_code == 401


def test_analizar_texto(cliente):
    asunto, cuerpo = CORREOS["phishing"]
    respuesta = cliente.post("/v1/analizar", headers=CABECERA, json={"asunto": asunto, "cuerpo": cuerpo})
    assert respuesta.status_code == 200
    VALIDADOR.validate(respuesta.json())
    assert respuesta.json()["clasificacion"]["clase"] == "phishing"


def test_analizar_correo_eml(cliente):
    eml = b"Subject: Verify\r\nContent-Type: text/plain\r\n\r\nverify your password at http://login.example.com/x\r\n"
    respuesta = cliente.post("/v1/analizar", headers=CABECERA, json={"eml_base64": base64.b64encode(eml).decode()})
    assert respuesta.status_code == 200
    assert respuesta.json()["correo"]["asunto_defang"] == "Verify"


@pytest.mark.parametrize("cuerpo", [{"cuerpo": "a", "eml_base64": "YQ=="}, {"asunto": "solo asunto"}])
def test_entrada_ambigua_responde_422(cliente, cuerpo):
    assert cliente.post("/v1/analizar", headers=CABECERA, json=cuerpo).status_code == 422


def test_base64_invalido_responde_400(cliente):
    respuesta = cliente.post("/v1/analizar", headers=CABECERA, json={"eml_base64": "@@no-base64@@"})
    assert respuesta.status_code == 400


def test_fallo_de_carga_responde_503():
    def cargador_con_fallo():
        raise RuntimeError("sin acceso al repositorio de modelos")

    with TestClient(crear_app(api_key=CLAVE, cargador=cargador_con_fallo)) as cliente_prueba:
        assert cliente_prueba.get("/salud").json()["estado"] == "sin_modelo"
        respuesta = cliente_prueba.post("/v1/analizar", headers=CABECERA, json={"cuerpo": "x"})
        assert respuesta.status_code == 503
