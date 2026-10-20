"""Funciones auxiliares: configuración, semillas, registro de eventos y rutas del proyecto."""

from __future__ import annotations

import logging
import os
import random
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_POR_DEFECTO = RAIZ / "config.yaml"


def cargar_config(ruta: str | Path | None = None) -> dict:
    """Lee el archivo de configuración YAML del proyecto.

    Args:
        ruta: Ruta alternativa. Por defecto se usa ``config.yaml`` en la raíz del repositorio,
            o la indicada en la variable de entorno ``G17_CONFIG``.
    """
    ruta = Path(ruta or os.environ.get("G17_CONFIG", CONFIG_POR_DEFECTO))
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {ruta}")
    with ruta.open(encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def fijar_semillas(semilla: int) -> None:
    """Fija las semillas de Python, NumPy y, si está instalado, PyTorch."""
    random.seed(semilla)
    np.random.seed(semilla)
    os.environ["PYTHONHASHSEED"] = str(semilla)
    try:
        import torch

        torch.manual_seed(semilla)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(semilla)
    except ImportError:
        pass


def configurar_logging(nivel: str = "INFO") -> logging.Logger:
    """Configura el registro de eventos del paquete con un formato uniforme."""
    logging.basicConfig(
        level=getattr(logging, nivel.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("g17")


def detectar_entorno() -> str:
    """Devuelve ``colab``, ``kaggle`` o ``local`` según dónde se ejecute el código."""
    if os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
        return "kaggle"
    try:
        import google.colab  # noqa: F401

        return "colab"
    except ImportError:
        return "local"


def ruta_datos(config: dict, entorno: str | None = None) -> Path:
    """Carpeta base de datos y artefactos según el entorno de ejecución.

    En Colab se espera Google Drive montado; en Kaggle, el directorio de trabajo; en local,
    la variable ``G17_BASE`` o la raíz del repositorio.
    """
    entorno = entorno or detectar_entorno()
    rutas = config["rutas"]
    if entorno == "colab":
        return Path(rutas["colab"])
    if entorno == "kaggle":
        return Path(rutas["kaggle"])
    return Path(os.environ.get("G17_BASE", RAIZ))
