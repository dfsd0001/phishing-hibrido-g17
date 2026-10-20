"""Servicio de inferencia (FastAPI) del detector de phishing.

Endpoints:
    GET  /salud         Estado del servicio, sin datos sensibles.
    POST /v1/analizar   Analiza un correo y devuelve el contrato JSON v1.2, validado contra el
                        esquema antes de responder.

Seguridad:
    * Clave en la cabecera ``X-API-Key``, comparada en tiempo constante.
    * Límites de tamaño en la solicitud.
    * El contenido de los correos nunca se escribe en el registro de eventos.
    * La salida pasa por el bloqueo de IOC vivos del detector.

Variables de entorno:
    API_KEY           Clave que deben presentar los clientes (obligatoria).
    MODEL_REPO        Repositorio de artefactos en Hugging Face Hub.
    MODEL_REVISION    Etiqueta de la versión publicada (por defecto ``v2``).
    HF_TOKEN          Token de solo lectura, necesario si el repositorio de modelos es privado.
    DOMINIOS_PROPIOS  Dominios de la organización separados por coma (opcional).
    UMBRAL_EN         Umbral operativo de la ruta inglesa (opcional, decisión D27).
"""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import jsonschema
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import model as modelo  # noqa: E402

log = logging.getLogger("g17.api")
VERSION_API = "1.1"
ESQUEMA = RAIZ / "contracts" / "contrato_v1.schema.json"

# Correos de calentamiento: la primera inferencia de cada ruta tarda varios segundos por la
# carga perezosa de los modelos. Se paga al arrancar el servicio y no en la primera consulta.
CALENTAMIENTO = (
    ("Weekly report", "Hi team, the weekly report is attached."),
    ("Informe semanal", "Hola equipo, adjunto el informe semanal del proyecto."),
)


def _validador_contrato() -> jsonschema.Draft202012Validator:
    esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(esquema, format_checker=jsonschema.FormatChecker())


class Solicitud(BaseModel):
    """Cuerpo de ``POST /v1/analizar``: texto (asunto y cuerpo) o correo completo en base64."""

    asunto: str = Field("", max_length=1_000)
    cuerpo: str | None = Field(None, max_length=500_000)
    eml_base64: str | None = Field(None, max_length=2_000_000)

    @model_validator(mode="after")
    def exactamente_una_entrada(self):
        if (self.cuerpo is None) == (self.eml_base64 is None):
            raise ValueError("Envíe 'cuerpo' (con 'asunto' opcional) o 'eml_base64', pero no ambos")
        return self


def cargar_detector_desde_hub() -> modelo.Detector:
    """Descarga los artefactos de la versión indicada y construye el detector."""
    from huggingface_hub import snapshot_download

    ruta = snapshot_download(
        repo_id=os.environ["MODEL_REPO"],
        revision=os.getenv("MODEL_REVISION", "v2"),
        token=os.getenv("HF_TOKEN") or None,
    )
    dominios = tuple(d.strip() for d in os.getenv("DOMINIOS_PROPIOS", "").split(",") if d.strip())
    umbral = os.getenv("UMBRAL_EN", "").strip()
    return modelo.Detector.desde_directorio(
        ruta, dominios_propios=dominios, umbral_en=float(umbral) if umbral else None
    )


def crear_app(detector=None, api_key: str | None = None, cargador=cargar_detector_desde_hub) -> FastAPI:
    """Construye la aplicación. Las pruebas inyectan un detector simulado y una clave fija."""
    estado = {
        "detector": detector,
        "api_key": api_key if api_key is not None else os.getenv("API_KEY", ""),
        "validador": _validador_contrato(),
        "carga_s": None,
        "error_carga": None,
    }

    @asynccontextmanager
    async def ciclo_de_vida(app):
        if estado["detector"] is None:
            inicio = time.time()
            try:
                estado["detector"] = cargador()
                for asunto, cuerpo in CALENTAMIENTO:
                    try:
                        estado["detector"].analizar(asunto, cuerpo)
                    except Exception:
                        log.warning("Calentamiento fallido; el servicio continúa")
            except Exception as error:
                # El servicio responde 503 en lugar de terminar.
                estado["error_carga"] = type(error).__name__
                log.exception("No se pudo cargar el modelo")
            estado["carga_s"] = round(time.time() - inicio, 1)
        yield

    app = FastAPI(title="G17 - Detector híbrido de phishing", version=VERSION_API, lifespan=ciclo_de_vida)

    def exigir_clave(x_api_key: str = Header(default="")):
        if not estado["api_key"]:
            raise HTTPException(503, "API_KEY no configurada en el servidor")
        if not hmac.compare_digest(x_api_key.encode(), estado["api_key"].encode()):
            raise HTTPException(401, "Clave inválida")

    @app.get("/salud")
    def salud():
        detector_actual = estado["detector"]
        return {
            "estado": "ok" if detector_actual else "sin_modelo",
            "version_api": VERSION_API,
            "version_contrato": modelo.VERSION_CONTRATO,
            "modelo": getattr(detector_actual, "version_modelo", None),
            "variante": getattr(detector_actual, "variante", None),
            "umbral_en": getattr(detector_actual, "umbral", None),
            "carga_s": estado["carga_s"],
            "error_carga": estado["error_carga"],
        }

    @app.post("/v1/analizar", dependencies=[Depends(exigir_clave)])
    def analizar(solicitud: Solicitud):
        detector_actual = estado["detector"]
        if detector_actual is None:
            raise HTTPException(503, "Modelo no disponible")
        crudo = None
        if solicitud.eml_base64 is not None:
            try:
                crudo = base64.b64decode(solicitud.eml_base64, validate=True)
            except (binascii.Error, ValueError):
                raise HTTPException(400, "eml_base64 inválido") from None
        try:
            salida = detector_actual.analizar(solicitud.asunto, solicitud.cuerpo or "", crudo=crudo)
        except RuntimeError:
            log.error("Respuesta bloqueada por contener un IOC vivo")
            raise HTTPException(500, "Respuesta bloqueada por la política de defanging") from None
        try:
            estado["validador"].validate(salida)
        except jsonschema.ValidationError:
            log.error("Salida fuera de contrato (id %s)", salida.get("id_analisis"))
            raise HTTPException(500, "Salida fuera de contrato") from None
        return salida

    return app


app = crear_app()
