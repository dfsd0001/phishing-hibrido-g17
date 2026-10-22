"""Inferencia dentro del proceso de la interfaz, para la demostración pública en la nube.

En el despliegue local la interfaz consulta la API (``cliente_api``). En Streamlit Community Cloud
no hay una API aparte: la interfaz carga el mismo detector publicado (``src.model.Detector``, versión
``v2`` de Hugging Face Hub) y valida cada salida contra el mismo contrato JSON v1.2, de modo que el
resultado es idéntico al de la API.

El modelo se carga una sola vez por proceso, en un hilo aparte, para que la página responda mientras
tanto; todas las sesiones de la aplicación comparten esa única copia.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path

import jsonschema

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import despliegue  # noqa: E402
from src import model as modelo  # noqa: E402

log = logging.getLogger("g17.motor_local")

_candado = threading.Lock()
_estado = {"detector": None, "error": None, "inicio": None, "carga_s": None, "hilo": None}
_validador = despliegue.validador_contrato()


def _cargar(cargador) -> None:
    try:
        detector = cargador()
        despliegue.calentar(detector)
        _estado["detector"] = detector
    except Exception as error:
        # El motivo queda en el registro de la plataforma; la interfaz solo informa que no hay modelo.
        _estado["error"] = type(error).__name__
        log.exception("No se pudo cargar el modelo")
    _estado["carga_s"] = round(time.time() - _estado["inicio"], 1)


def iniciar_carga(cargador=despliegue.cargar_detector_desde_hub) -> None:
    """Inicia la carga del modelo si todavía no empezó. No bloquea."""
    with _candado:
        if _estado["hilo"] is None:
            _estado["inicio"] = time.time()
            _estado["hilo"] = threading.Thread(target=_cargar, args=(cargador,), daemon=True, name="carga-modelo")
            _estado["hilo"].start()


def estado() -> dict:
    """Estado con la misma forma que ``GET /salud`` de la API."""
    iniciar_carga()
    detector = _estado["detector"]
    if detector is not None:
        situacion = "ok"
    elif _estado["error"] is not None:
        situacion = "sin_modelo"
    else:
        situacion = "cargando"
    return {
        "estado": situacion,
        "version_api": None,
        "version_contrato": modelo.VERSION_CONTRATO,
        "modelo": getattr(detector, "version_modelo", None),
        "variante": getattr(detector, "variante", None),
        "umbral_en": getattr(detector, "umbral", None),
        "carga_s": _estado["carga_s"],
        "error_carga": _estado["error"],
    }


def analizar(asunto: str, cuerpo: str, eml: bytes | None, error_tipo) -> dict:
    """Analiza un correo con el detector cargado y valida la salida contra el contrato.

    Args:
        error_tipo: Clase de excepción de la interfaz (``cliente_api.ErrorAPI``).
    """
    iniciar_carga()
    detector = _estado["detector"]
    if detector is None:
        raise error_tipo("modelo_no_disponible")
    try:
        salida = detector.analizar(asunto, cuerpo, crudo=eml)
    except RuntimeError as error:
        # El detector bloquea cualquier salida con un indicador vivo.
        log.error("Respuesta bloqueada por la política de defanging")
        raise error_tipo("error_servidor") from error
    except Exception as error:
        log.exception("Fallo del detector")
        raise error_tipo("entrada_invalida" if eml is not None else "error_servidor") from error
    try:
        _validador.validate(salida)
    except jsonschema.ValidationError as error:
        log.error("Salida fuera de contrato (id %s)", salida.get("id_analisis"))
        raise error_tipo("respuesta_invalida") from error
    return salida


def reiniciar_para_pruebas(detector=None) -> None:
    """Deja el motor en un estado conocido. Solo para las pruebas automáticas."""
    _estado.update({"detector": detector, "error": None, "inicio": time.time(), "carga_s": 0.0,
                    "hilo": None if detector is None else threading.current_thread()})
