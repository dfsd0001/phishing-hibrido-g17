"""Punto de entrada de la demostración pública en Streamlit Community Cloud.

Ejecuta la misma interfaz de ``app/app.py`` en modo ``local``: el detector publicado (versión ``v2``
de Hugging Face Hub) se carga dentro de la aplicación, sin una API aparte. Las dependencias de esta
carpeta (``requirements.txt``) son las mínimas para la inferencia en CPU.

Secretos de la plataforma (Settings, Secrets), en formato TOML:

    HF_TOKEN = "<token de solo lectura del repositorio de modelos>"
    UMBRAL_EN = "0.8586"

Opcionales: ``MODEL_REPO``, ``MODEL_REVISION`` y ``G17_LIMITE_SESION``. Ver ``nube/README.md``.
"""

import os
import runpy
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (RAIZ, RAIZ / "app"):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))

os.environ.setdefault("G17_MODO", "local")
os.environ.setdefault("UMBRAL_EN", "0.8586")
os.environ.setdefault("G17_LIMITE_SESION", "30")

runpy.run_path(str(RAIZ / "app" / "app.py"), run_name="__main__")
