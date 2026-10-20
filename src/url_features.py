"""Variables léxicas de una URL, calculadas solo a partir de la cadena.

El módulo nunca resuelve DNS ni abre conexiones. Recibe la URL viva únicamente en memoria
(ver ``ioc_utils.urls_para_features``).

Se excluyen a propósito el esquema (http/https) y el prefijo ``www``: en PhiUSIIL el 100 %
de las URL legítimas usa el esquema https con prefijo www, frente al 49 % y 41 % del phishing. Un modelo que
viera esas marcas aprendería el procedimiento de recolección del dataset y no la malicia de
la URL.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from urllib.parse import urlsplit

_ESQUEMA = re.compile(r"(?i)^[a-z][a-z0-9+.-]*://")
_IP = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_TOKENS = re.compile(r"[^a-z0-9]+")

ESPECIALES = "@~%=&_-!*,;$+"

# Palabras frecuentes en URL de phishing según la literatura de detección por URL.
PALABRAS_SENSIBLES = (
    "login",
    "signin",
    "verify",
    "account",
    "update",
    "secure",
    "banking",
    "confirm",
    "password",
    "webscr",
    "wallet",
    "invoice",
)

NUMERICAS = [
    "url_len",
    "host_len",
    "path_len",
    "query_len",
    "n_puntos_host",
    "n_subdominios",
    "n_guiones_host",
    "n_digitos_host",
    "ratio_digitos",
    "host_es_ip",
    "tiene_puerto",
    "n_segmentos_path",
    "n_params",
    "n_especiales",
    "tiene_arroba",
    "doble_barra_path",
    "entropia_host",
    "entropia_resto",
    "max_token_len",
    "tiene_punycode",
    "n_palabras_sensibles",
    "tld_len",
]
CATEGORICAS = ["tld"]


def _entropia(cadena: str) -> float:
    """Entropía de Shannon (bits por carácter)."""
    if not cadena:
        return 0.0
    n = len(cadena)
    return -sum(v / n * math.log2(v / n) for v in Counter(cadena).values())


def descomponer(url: str) -> tuple[str, int | None, str, str, bool]:
    """Separa una URL en host (sin ``www``), puerto, ruta, consulta e indicador de userinfo.

    Es tolerante a URL mal formadas y nunca lanza excepciones. El indicador de userinfo
    detecta el engaño ``marca-legitima.com@host-real``, donde lo anterior a ``@`` no es el host.
    """
    candidata = url.strip()
    if not _ESQUEMA.match(candidata):
        candidata = "http://" + candidata
    try:
        partes = urlsplit(candidata)
        host = (partes.hostname or "").lower().rstrip(".")
        try:
            puerto = partes.port
        except ValueError:
            puerto = None
        ruta, consulta = partes.path or "", partes.query or ""
        userinfo = "@" in (partes.netloc or "")
    except ValueError:
        # Por ejemplo, corchetes de IPv6 inválidos: se separa a mano.
        resto = _ESQUEMA.sub("", candidata)
        host, _, cola = resto.partition("/")
        userinfo = "@" in host
        host = host.rsplit("@", 1)[-1].lower()
        puerto, ruta, consulta = None, "/" + cola, ""
    if host.startswith("www."):
        host = host[4:]
    return host, puerto, ruta, consulta, userinfo


def features_url(url: str) -> dict:
    """Calcula las 22 variables numéricas y el TLD de una URL.

    El conteo de subdominios no usa una lista de sufijos públicos, por lo que
    ``a.example.co.uk`` cuenta dos subdominios (limitación documentada).
    """
    host, puerto, ruta, consulta, userinfo = descomponer(url)
    resto = host + ruta + ("?" + consulta if consulta else "")
    resto_min = resto.lower()
    es_ip = bool(_IP.match(host))
    if es_ip:
        tld = "__ip__"
    else:
        tld = host.rsplit(".", 1)[-1] if "." in host else "__sin_tld__"
    tokens = [t for t in _TOKENS.split(resto_min) if t]
    return {
        "url_len": len(resto),
        "host_len": len(host),
        "path_len": len(ruta),
        "query_len": len(consulta),
        "n_puntos_host": host.count("."),
        "n_subdominios": 0 if es_ip else max(0, host.count(".") - 1),
        "n_guiones_host": host.count("-"),
        "n_digitos_host": sum(c.isdigit() for c in host),
        "ratio_digitos": sum(c.isdigit() for c in resto) / max(len(resto), 1),
        "host_es_ip": int(es_ip),
        "tiene_puerto": int(puerto is not None),
        "n_segmentos_path": len([s for s in ruta.split("/") if s]),
        "n_params": (consulta.count("&") + 1) if consulta else 0,
        "n_especiales": sum(resto.count(c) for c in ESPECIALES),
        "tiene_arroba": int(userinfo or "@" in resto),
        "doble_barra_path": int("//" in ruta),
        "entropia_host": _entropia(host),
        "entropia_resto": _entropia(resto),
        "max_token_len": max((len(t) for t in tokens), default=0),
        "tiene_punycode": int("xn--" in host),
        "n_palabras_sensibles": sum(resto_min.count(p) for p in PALABRAS_SENSIBLES),
        "tld_len": 0 if es_ip else len(tld),
        "tld": tld,
    }
