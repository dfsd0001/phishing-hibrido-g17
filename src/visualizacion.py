"""Estilo común de las figuras de los notebooks y de la documentación.

Los colores de las clases siguen un orden categórico fijo validado para daltonismo
(adyacentes con diferencia perceptual suficiente) y se usan siempre para la misma clase.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

COLORES_CLASE = {"legitimo": "#2a78d6", "spam": "#eb6834", "phishing": "#1baf7a"}
# Orden fijo para comparar modelos o escenarios (mismo criterio que las clases)
COLORES_SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
TEXTO_PRINCIPAL = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
REJILLA = "#e4e3df"
NOMBRES_CLASE = {"legitimo": "Legítimo", "spam": "Spam", "phishing": "Phishing"}


def miles(numero: float) -> str:
    """Número entero con punto como separador de miles, como se escribe en español (39.154)."""
    return f"{round(numero):,}".replace(",", ".")


def aplicar_estilo() -> None:
    """Configura matplotlib con marcas finas, rejilla tenue y texto en tinta neutra."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": REJILLA,
            "axes.labelcolor": TEXTO_SECUNDARIO,
            "axes.titlecolor": TEXTO_PRINCIPAL,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 9.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": REJILLA,
            "grid.linewidth": 0.8,
            "xtick.color": TEXTO_SECUNDARIO,
            "ytick.color": TEXTO_SECUNDARIO,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "lines.linewidth": 2,
            "lines.markersize": 6,
            "font.family": "DejaVu Sans",
        }
    )


def guardar_figura(figura: plt.Figure, ruta: str | Path) -> Path:
    """Guarda la figura en PNG, creando la carpeta si no existe, y devuelve la ruta."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(ruta)
    return ruta
