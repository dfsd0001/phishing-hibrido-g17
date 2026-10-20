"""Extracción, defanging y refanging de indicadores de compromiso (IOC).

Política de seguridad del proyecto:

* Todo IOC que se almacena, reporta o emite sale defangeado, por ejemplo
  ``hxxps[://]dominio[.]com`` o ``192[.]0[.]2[.]1``.
* El refang solo existe para calcular variables en memoria (``urls_para_features``).
* El módulo no resuelve DNS ni abre conexiones: únicamente transforma cadenas.

Alcance: URL con esquema (http, https, ftp) o con prefijo ``www.``, e IPv4. Quedan fuera
los dominios sueltos sin esquema ni ``www`` (generan demasiados falsos positivos del tipo
``archivo.txt``), IPv6, URL codificadas en porcentaje y direcciones de correo.
"""

from __future__ import annotations

import re

_REFANG = [
    (re.compile(r"(?i)\bhxxp"), "http"),
    (re.compile(r"(?i)\bfxp"), "ftp"),
    (re.compile(r"\[:\/\/\]"), "://"),
    (re.compile(r"\[:\]"), ":"),
    (re.compile(r"\[\.\]|\(\.\)|\{\.\}|\[dot\]", re.I), "."),
]

# Se excluyen los corchetes para no fusionar enlaces Markdown del tipo [texto](url).
_URL = re.compile(r"(?i)\b(?:https?|ftp)://[^\s<>\"'`\[\]]+|\bwww\.[^\s<>\"'`\[\]]+")
_PREFIJO = re.compile(r"(?i)^(?:(?:https?|ftp)://|www\.)")

# Separa URL pegadas por coma, punto y coma o barra vertical, frecuentes en listas CSP o HTML.
_CORTE_LISTA = re.compile(r"(?i)[,;|](?=(?:https?|ftp)://|www\.)")

_OCTETO = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"

# La IPv4 no puede estar pegada a otro dígito ni formar parte de una versión (1.2.3.4.5),
# pero sí admite un punto o una coma de cierre de oración.
_IPV4 = re.compile(rf"(?<!\d)(?<!\d\.){_OCTETO}(?:\.{_OCTETO}){{3}}(?!\d)(?!\.\d)")

# Una URL es válida solo si después del prefijo empieza un host alfanumérico (Unicode).
_VALIDA = re.compile(r"(?i)^(?:(?:https?|ftp)://|www\.)[^\W_]")

# Puntuación que suele quedar pegada al final de una URL escrita en prosa.
_COLA = ".,;:!?)]}'\">"

# Esquema pegado a texto previo sin separador ("...com.mxhttps://x"). Es una ofuscación
# observada en el corpus SpaPhish: se separa para que la URL se detecte completa.
_ESQUEMA_PEGADO = re.compile(r"(?i)(?<=[^\s/:])(?=(?:https?|ftp)://)")


def refang(texto: str) -> str:
    """Revierte el defanging de un texto.

    El resultado contiene IOC ejecutables y solo debe usarse en memoria.
    """
    for patron, reemplazo in _REFANG:
        texto = patron.sub(reemplazo, texto)
    return _ESQUEMA_PEGADO.sub(" ", texto)


def _limpiar_cola(url: str) -> str:
    """Elimina la puntuación final ajena a la URL, conservando paréntesis balanceados."""
    while url and url[-1] in _COLA:
        if url[-1] == ")" and url.count("(") >= url.count(")"):
            break
        url = url[:-1]
    return url


def defang_ip(ip: str) -> str:
    """Neutraliza una IPv4: ``192.0.2.1`` pasa a ``192[.]0[.]2[.]1``."""
    return ip.replace(".", "[.]")


def defang_url(url: str) -> str:
    """Devuelve la forma defangeada canónica de una URL.

    La función es idempotente: primero refanga y luego aplica el defanging. Neutraliza
    también los esquemas anidados en el host, la ruta o los parámetros, un patrón
    habitual en redirecciones abiertas usadas por campañas de phishing.
    """
    url = refang(url)
    coincidencia = re.match(r"(?i)^([a-z][a-z0-9+.-]*)://(.*)$", url)
    if coincidencia:
        esquema = re.sub(r"(?i)^http", "hxxp", coincidencia.group(1))
        esquema = re.sub(r"(?i)^ftp", "fxp", esquema)
        resto, prefijo = coincidencia.group(2), f"{esquema}[://]"
    else:
        resto, prefijo = url, ""

    # Un host mal delimitado puede terminar en "https:" y la ruta empezar con "//dominio".
    resto = re.sub(r"(?i)\bhttp", "hxxp", resto)
    resto = re.sub(r"(?i)\bftp(?=s?://)", "fxp", resto)

    corte = re.search(r"[/?#]", resto)
    if corte:
        host, cola = resto[: corte.start()], resto[corte.start() :]
    else:
        host, cola = resto, ""
    host = host.replace(".", "[.]")

    cola = re.sub(r"(?i)\bhttp", "hxxp", cola)
    cola = re.sub(r"(?i)\bftp://", "fxp://", cola)
    cola = cola.replace("://", "[://]")
    cola = re.sub(r"(?i)\bwww\.", "www[.]", cola)
    cola = _IPV4.sub(lambda m: defang_ip(m.group(0)), cola)
    return prefijo + host + cola


def _es_valida(url: str) -> bool:
    return bool(_VALIDA.match(url))


def _degenerado(url: str) -> bool:
    """Indica si la cadena no tiene ningún carácter alfanumérico tras el prefijo."""
    prefijo = _PREFIJO.match(url)
    if not prefijo:
        # La limpieza de puntuación eliminó el prefijo ("www..." queda en "www").
        return True
    return not re.search(r"[^\W_]", url[prefijo.end() :])


def _clave(url: str) -> str:
    """Clave de deduplicación: esquema y host en minúsculas; la ruta conserva mayúsculas."""
    partes = re.match(r"(?i)^([a-z]+://)?([^/?#]*)(.*)$", url)
    return (partes.group(1) or "").lower() + partes.group(2).lower() + partes.group(3)


def urls_para_features(texto: str) -> list[str]:
    """Devuelve las URL vivas, deduplicadas y en orden de aparición.

    Acepta texto ya defangeado. El resultado sirve solo para calcular variables en memoria:
    no debe persistirse ni mostrarse.
    """
    vistos: set[str] = set()
    salida: list[str] = []
    for coincidencia in _URL.finditer(refang(texto)):
        for trozo in _CORTE_LISTA.split(coincidencia.group(0)):
            url = _limpiar_cola(trozo)
            if url and _es_valida(url) and _clave(url) not in vistos:
                vistos.add(_clave(url))
                salida.append(url)
    return salida


def extraer_iocs(texto: str) -> dict:
    """Extrae las URL e IPv4 de un texto, siempre defangeadas.

    Returns:
        Diccionario con las listas ``urls`` e ``ips``, sus conteos y el indicador ``sin_url``.
    """
    vivo = refang(texto)
    urls = urls_para_features(vivo)
    ips = list(dict.fromkeys(_IPV4.findall(_URL.sub(" ", vivo))))
    return {
        "urls": [defang_url(u) for u in urls],
        "ips": [defang_ip(i) for i in ips],
        "n_urls": len(urls),
        "n_ips": len(ips),
        "sin_url": len(urls) == 0,
    }


def defang_texto(texto: str) -> str:
    """Devuelve el texto completo con todas sus URL e IPv4 neutralizadas."""
    vivo = refang(texto)

    def _sustituir(coincidencia: re.Match) -> str:
        url = coincidencia.group(0)
        limpio = _limpiar_cola(url)
        if _degenerado(limpio):
            return url
        return defang_url(limpio) + url[len(limpio) :]

    vivo = _URL.sub(_sustituir, vivo)
    return _IPV4.sub(lambda m: defang_ip(m.group(0)), vivo)


def iocs_vivos(texto: str) -> list[str]:
    """Control de calidad del KPI de defanging: lista los IOC que siguen ejecutables.

    Es más estricto que el defanger: cualquier URL no degenerada cuenta como viva.
    """
    vivos = [m.group(0) for m in _URL.finditer(texto) if not _degenerado(_limpiar_cola(m.group(0)))]
    vivos += _IPV4.findall(_URL.sub(" ", texto))
    return vivos
