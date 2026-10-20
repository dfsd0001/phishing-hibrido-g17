"""Pruebas de las variables léxicas de URL (dominios reservados RFC 2606 e IP RFC 5737)."""

import pytest

from src.url_features import CATEGORICAS, NUMERICAS, features_url


def test_invariante_a_esquema_y_www():
    """El artefacto de recolección de PhiUSIIL (esquema y www) no puede entrar al modelo."""
    referencia = features_url("https://www.example.com/login?a=1")
    for variante in ("http://example.com/login?a=1", "example.com/login?a=1", "HTTPS://WWW.EXAMPLE.COM/login?a=1"):
        assert features_url(variante) == referencia


def test_valores_basicos():
    variables = features_url("http://secure-login.bank.corp.example.com:8080/a/b//c?x=1&y=2")
    assert variables["host_es_ip"] == 0
    assert variables["tiene_puerto"] == 1
    assert variables["n_params"] == 2
    assert variables["n_subdominios"] == 3
    assert variables["n_guiones_host"] == 1
    assert variables["doble_barra_path"] == 1
    assert variables["tld"] == "com"
    assert variables["n_palabras_sensibles"] >= 2


def test_host_ip():
    variables = features_url("http://192.0.2.10/admin")
    assert variables["host_es_ip"] == 1
    assert variables["tld"] == "__ip__"
    assert variables["n_subdominios"] == 0


def test_punycode_y_arroba():
    variables = features_url("http://user@xn--pypal-4ve.example.com/")
    assert variables["tiene_arroba"] == 1
    assert variables["tiene_punycode"] == 1


@pytest.mark.parametrize("url", ["http://[::1", "http://", "::::", "http://a b", "", "http://example.com:99999/"])
def test_url_mal_formada_nunca_lanza(url):
    assert set(features_url(url)) == set(NUMERICAS + CATEGORICAS)


def test_truco_arroba_en_la_autoridad():
    variables = features_url("http://bank.example.com@evil.example.net/login")
    assert variables["tiene_arroba"] == 1
    assert variables["tld"] == "net"
