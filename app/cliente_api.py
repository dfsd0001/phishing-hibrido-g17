"""Cliente de la API del detector para la interfaz.

La interfaz no carga los modelos: envía el correo a la API (``POST /v1/analizar``) y muestra el
contrato JSON que recibe. Así la interfaz y la integración con el SOC usan exactamente el mismo
servicio. Los errores se traducen a una excepción con un código que la interfaz explica al
usuario; el texto del correo nunca se registra.

Variables de entorno:
    G17_API_URL   Dirección de la API (por defecto ``http://localhost:8000``).
    G17_API_KEY   Clave de la API (cabecera ``X-API-Key``).
    G17_TIMEOUT   Tiempo máximo de espera en segundos (por defecto 60).
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass

import httpx

log = logging.getLogger("g17.interfaz")

MAX_CARACTERES_CUERPO = 500_000
MAX_CARACTERES_ASUNTO = 1_000
MAX_BYTES_EML = 1_500_000


class ErrorAPI(Exception):
    """Fallo al consultar la API, con un código estable para mostrar un mensaje al usuario.

    Códigos: ``sin_conexion``, ``tiempo_agotado``, ``clave_invalida``, ``modelo_no_disponible``,
    ``entrada_invalida``, ``error_servidor`` y ``respuesta_invalida``.
    """

    def __init__(self, codigo: str, detalle: str = ""):
        super().__init__(f"{codigo}: {detalle}" if detalle else codigo)
        self.codigo = codigo
        self.detalle = detalle


@dataclass(frozen=True)
class Configuracion:
    url: str
    clave: str
    timeout: float

    @classmethod
    def desde_entorno(cls) -> Configuracion:
        return cls(
            url=os.getenv("G17_API_URL", "http://localhost:8000").rstrip("/"),
            clave=os.getenv("G17_API_KEY", ""),
            timeout=float(os.getenv("G17_TIMEOUT", "60")),
        )


def validar_entrada(asunto: str, cuerpo: str, eml: bytes | None) -> list[str]:
    """Devuelve la lista de problemas de la entrada (vacía si es válida).

    Los códigos se traducen en la interfaz: ``vacio``, ``asunto_largo``, ``cuerpo_largo`` y
    ``eml_grande``.
    """
    problemas = []
    if eml is not None:
        if len(eml) > MAX_BYTES_EML:
            problemas.append("eml_grande")
        return problemas
    if not (asunto.strip() or cuerpo.strip()):
        problemas.append("vacio")
    if len(asunto) > MAX_CARACTERES_ASUNTO:
        problemas.append("asunto_largo")
    if len(cuerpo) > MAX_CARACTERES_CUERPO:
        problemas.append("cuerpo_largo")
    return problemas


def _cliente(configuracion: Configuracion, transporte: httpx.BaseTransport | None) -> httpx.Client:
    return httpx.Client(base_url=configuracion.url, timeout=configuracion.timeout, transport=transporte)


def estado_servicio(
    configuracion: Configuracion | None = None, transporte: httpx.BaseTransport | None = None
) -> dict | None:
    """Respuesta de ``GET /salud`` o ``None`` si la API no responde."""
    configuracion = configuracion or Configuracion.desde_entorno()
    try:
        with _cliente(configuracion, transporte) as cliente:
            respuesta = cliente.get("/salud", timeout=5)
            respuesta.raise_for_status()
            return respuesta.json()
    except (httpx.HTTPError, ValueError):
        return None


def analizar(
    asunto: str = "",
    cuerpo: str = "",
    eml: bytes | None = None,
    configuracion: Configuracion | None = None,
    transporte: httpx.BaseTransport | None = None,
) -> dict:
    """Envía un correo a la API y devuelve el contrato JSON v1.2.

    Args:
        asunto: Asunto del correo.
        cuerpo: Cuerpo en texto o HTML.
        eml: Correo completo (.eml). Si se entrega, reemplaza a asunto y cuerpo.
        transporte: Transporte alternativo de httpx, usado en las pruebas.

    Raises:
        ErrorAPI: Con el código del problema.
    """
    configuracion = configuracion or Configuracion.desde_entorno()
    if eml is not None:
        cuerpo_solicitud = {"eml_base64": base64.b64encode(eml).decode("ascii")}
    else:
        cuerpo_solicitud = {"asunto": asunto, "cuerpo": cuerpo}
    try:
        with _cliente(configuracion, transporte) as cliente:
            respuesta = cliente.post("/v1/analizar", json=cuerpo_solicitud, headers={"X-API-Key": configuracion.clave})
    except httpx.TimeoutException as error:
        raise ErrorAPI("tiempo_agotado") from error
    except httpx.HTTPError as error:
        log.warning("No se pudo conectar con la API en %s", configuracion.url)
        raise ErrorAPI("sin_conexion", configuracion.url) from error

    codigos = {401: "clave_invalida", 400: "entrada_invalida", 422: "entrada_invalida", 503: "modelo_no_disponible"}
    if respuesta.status_code != 200:
        codigo = codigos.get(respuesta.status_code, "error_servidor")
        log.warning("La API respondió %s", respuesta.status_code)
        raise ErrorAPI(codigo, str(respuesta.status_code))
    try:
        salida = respuesta.json()
        salida["clasificacion"]["clase"]
    except (ValueError, KeyError, TypeError) as error:
        raise ErrorAPI("respuesta_invalida") from error
    return salida
