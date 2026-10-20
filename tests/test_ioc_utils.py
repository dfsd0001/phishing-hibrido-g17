"""Pruebas de extracción y defanging de IOC.

Todos los dominios de prueba son reservados para documentación (RFC 2606, ``example.*``) y
las direcciones IPv4 pertenecen a los rangos de documentación (RFC 5737).
"""

import random
import string

import pytest

from src.ioc_utils import (
    defang_ip,
    defang_texto,
    defang_url,
    extraer_iocs,
    iocs_vivos,
    refang,
    urls_para_features,
)


def test_defang_url_canonico():
    resultado = defang_url("https://login.example.com/path?a=1")
    assert resultado == "hxxps[://]login[.]example[.]com/path?a=1"


def test_defang_es_idempotente():
    url = "http://a.example.org/x"
    assert defang_url(defang_url(url)) == defang_url(url)


def test_refang_revierte_defang():
    url = "https://sub.example.net:8443/a.php?q=1"
    assert refang(defang_url(url)) == url


def test_www_sin_esquema():
    assert defang_url("www.example.com/login") == "www[.]example[.]com/login"


def test_redireccion_anidada_queda_neutralizada():
    resultado = defang_url("https://example.com/r?u=http://evil.example.net/p&ip=192.0.2.7")
    assert iocs_vivos(resultado) == []
    assert "hxxp[://]evil" in resultado
    assert "192[.]0[.]2[.]7" in resultado


def test_ip_en_host():
    assert defang_url("http://192.0.2.10/admin") == "hxxp[://]192[.]0[.]2[.]10/admin"


def test_defang_ip():
    assert defang_ip("198.51.100.4") == "198[.]51[.]100[.]4"


def test_ip_invalida_no_se_extrae():
    resultado = extraer_iocs("versión 999.1.1.1 y 10.0.0.300; válida 198.51.100.4")
    assert resultado["ips"] == ["198[.]51[.]100[.]4"]


def test_puntuacion_final_no_forma_parte_de_la_url():
    assert urls_para_features("Entra en https://example.com/verify.") == ["https://example.com/verify"]
    assert urls_para_features("(ver https://example.com/a)") == ["https://example.com/a"]


def test_href_html():
    cuerpo = '<a href="https://pay.example.com/x">Pagar</a>'
    assert urls_para_features(cuerpo) == ["https://pay.example.com/x"]


def test_extrae_de_texto_ya_defangeado():
    resultado = extraer_iocs("Clic en hxxps[://]secure[.]example[.]com/login ahora")
    assert resultado["urls"] == ["hxxps[://]secure[.]example[.]com/login"]
    assert resultado["n_urls"] == 1


def test_deduplica_ignorando_mayusculas_del_host():
    assert len(urls_para_features("HTTP://EXAMPLE.COM/a http://EXAMPLE.COM/a")) == 1


def test_texto_sin_url():
    resultado = extraer_iocs("Reunión mañana a las 10.30, sin enlaces.")
    assert resultado["sin_url"]
    assert resultado["n_urls"] == 0
    assert resultado["ips"] == []


def test_ip_dentro_de_url_no_se_duplica():
    resultado = extraer_iocs("http://192.0.2.1/x")
    assert resultado["ips"] == []
    assert resultado["n_urls"] == 1


def test_defang_texto_conserva_la_prosa():
    texto = "Estimado cliente, valide en https://bank.example.com/login. Servidor 192.0.2.5."
    resultado = defang_texto(texto)
    assert iocs_vivos(resultado) == []
    assert resultado.startswith("Estimado cliente, valide en hxxps[://]bank[.]example[.]com/login.")
    assert resultado.endswith("Servidor 192[.]0[.]2[.]5.")


def test_iocs_vivos_detecta_url_e_ip():
    assert iocs_vivos("http://example.com")
    assert iocs_vivos("198.51.100.1")


def _texto_aleatorio(generador: random.Random) -> str:
    trozos = []
    for _ in range(generador.randint(1, 12)):
        tipo = generador.random()
        if tipo < 0.3:
            etiquetas = [generador.choice(["a", "login", "pay", "x1"]) for _ in range(generador.randint(1, 3))]
            host = ".".join(etiquetas) + ".example.com"
            ruta = "/" + "".join(generador.choices(string.ascii_letters + "/.?=&", k=generador.randint(0, 15)))
            esquema = generador.choice(["http://", "https://", "HTTPS://", "www.", "ftp://"])
            trozos.append(esquema + host + ruta + generador.choice(["", ".", ")", ","]))
        elif tipo < 0.45:
            trozos.append(".".join(str(generador.randint(0, 255)) for _ in range(4)))
        elif tipo < 0.55:
            trozos.append("https://r.example.com/?u=http://inner.example.org/")
        else:
            trozos.append("".join(generador.choices(string.ascii_letters + " .,:;()", k=generador.randint(1, 20))))
    return " ".join(trozos)


@pytest.mark.parametrize("semilla", range(300))
def test_propiedad_ningun_ioc_vivo_tras_defang(semilla):
    """Propiedad del KPI de defanging: tras ``defang_texto`` no queda ningún IOC vivo."""
    texto = _texto_aleatorio(random.Random(semilla))
    resultado = defang_texto(texto)
    assert iocs_vivos(resultado) == [], resultado


@pytest.mark.parametrize("texto", ["visita www... ahora", "www.)", "WWW..", "url: www.,x", "ver http://... luego"])
def test_cadenas_degeneradas_no_son_url(texto):
    assert urls_para_features(texto) == []
    assert iocs_vivos(defang_texto(texto)) == []


@pytest.mark.parametrize(
    ("texto", "ip"),
    [
        ("Servidor 192.0.2.5.", "192[.]0[.]2[.]5"),
        ("ip:198.51.100.7, puerto", "198[.]51[.]100[.]7"),
        ("fin 192.0.2.9!", "192[.]0[.]2[.]9"),
    ],
)
def test_ip_seguida_de_puntuacion(texto, ip):
    assert extraer_iocs(texto)["ips"] == [ip]
    assert iocs_vivos(defang_texto(texto)) == []


def test_numero_de_version_no_es_ip():
    assert extraer_iocs("version 1.2.3.4.5 y 10.1.2.3.4")["ips"] == []


def test_verificador_detecta_ip_al_final_de_oracion():
    assert iocs_vivos("conectar a 192.0.2.5.") == ["192.0.2.5"]


def test_dominio_internacionalizado():
    assert urls_para_features("https://ñandú.example.com/x") == ["https://ñandú.example.com/x"]


def test_enlace_markdown_no_reconstruye_url_viva():
    texto = "Soporte: [https://support.example.com](https://support.example.com)"
    assert urls_para_features(texto) == ["https://support.example.com"]
    assert iocs_vivos(defang_texto(texto)) == []


def test_url_tras_comodin_en_lista_csp():
    texto = "frame-src https://*.cdn.example.net,https://content.example.org/x;"
    assert "https://content.example.org/x" in urls_para_features(texto)
    assert iocs_vivos(defang_texto(texto)) == []
    assert iocs_vivos("https://*.cdn.example.net,https://content.example.org/x")


@pytest.mark.parametrize(
    "texto",
    [
        "le coût minimum http://http://spam.example.com ",
        "Click: http://http://192.0.2.75/login.verify/ HERE",
        "Head over to\n> http://http://software.example.org/search, enter",
    ],
)
def test_esquema_duplicado(texto):
    assert iocs_vivos(defang_texto(texto)) == []


@pytest.mark.parametrize(
    "texto",
    [
        "www.banco.example.comhttps://evil.example.com",
        "...comhttp://b.example.org/x",
        "texto.eshttps://phish.example.net/login",
    ],
)
def test_esquema_pegado_a_texto_previo(texto):
    assert iocs_vivos(defang_texto(texto)) == []
