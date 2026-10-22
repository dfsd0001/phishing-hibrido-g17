"""Carga del detector publicado y validación del contrato, comunes a la API y a la interfaz en la nube.

El modelo vive en un repositorio privado de Hugging Face Hub. Quien lo despliega entrega un token de
solo lectura por una variable de entorno o un secreto de la plataforma; el token nunca se escribe en
el código ni en el repositorio.

Variables de entorno:
    MODEL_REPO        Repositorio de artefactos (por defecto ``dennysSalazar/g17-phishing-hibrido``).
    MODEL_REVISION    Etiqueta de la versión publicada (por defecto ``v2``).
    HF_TOKEN          Token de solo lectura, necesario porque el repositorio es privado.
    DOMINIOS_PROPIOS  Dominios de la organización separados por coma (opcional).
    UMBRAL_EN         Umbral operativo de la ruta inglesa (decisión D27). Vacío: umbral de validación.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import jsonschema

from src import model as modelo

log = logging.getLogger("g17.despliegue")

RAIZ = Path(__file__).resolve().parents[1]
ESQUEMA = RAIZ / "contracts" / "contrato_v1.schema.json"
REPOSITORIO_POR_DEFECTO = "dennysSalazar/g17-phishing-hibrido"

# Correos de calentamiento: la primera inferencia de cada ruta tarda varios segundos por la carga
# perezosa de los modelos (decisión D25). Se paga al arrancar y no en la primera consulta.
CALENTAMIENTO = (
    ("Weekly report", "Hi team, the weekly report is attached."),
    ("Informe semanal", "Hola equipo, adjunto el informe semanal del proyecto."),
)


def validador_contrato() -> jsonschema.Draft202012Validator:
    """Validador del contrato JSON v1.2, el mismo que usan la API y las pruebas."""
    esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(esquema, format_checker=jsonschema.FormatChecker())


def cargar_detector_desde_hub() -> modelo.Detector:
    """Descarga los artefactos de la versión indicada y construye el detector."""
    from huggingface_hub import snapshot_download

    ruta = snapshot_download(
        repo_id=os.getenv("MODEL_REPO") or REPOSITORIO_POR_DEFECTO,
        revision=os.getenv("MODEL_REVISION") or "v2",
        token=os.getenv("HF_TOKEN") or None,
        allow_patterns=["models/*"],
    )
    dominios = tuple(d.strip() for d in os.getenv("DOMINIOS_PROPIOS", "").split(",") if d.strip())
    umbral = os.getenv("UMBRAL_EN", "").strip()
    return modelo.Detector.desde_directorio(
        ruta, dominios_propios=dominios, umbral_en=float(umbral) if umbral else None
    )


def calentar(detector: modelo.Detector) -> None:
    """Ejecuta una inferencia por ruta para que la primera consulta real no pague la carga."""
    for asunto, cuerpo in CALENTAMIENTO:
        try:
            detector.analizar(asunto, cuerpo)
        except Exception:
            log.warning("Calentamiento fallido; el servicio continúa")
