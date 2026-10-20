"""Controles de formato sobre los notebooks versionados."""

import json
from pathlib import Path

import nbformat
import pytest

RAIZ = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((RAIZ / "notebooks").rglob("*.ipynb"))


@pytest.mark.parametrize("ruta", NOTEBOOKS, ids=lambda r: r.name)
def test_formato_valido(ruta):
    nbformat.validate(nbformat.read(ruta, as_version=4))


@pytest.mark.parametrize("ruta", NOTEBOOKS, ids=lambda r: r.name)
def test_sin_estado_de_widgets(ruta):
    """El estado de widgets de Colab impide que GitHub muestre el notebook."""
    assert "widgets" not in json.loads(ruta.read_text(encoding="utf-8")).get("metadata", {})


@pytest.mark.parametrize("ruta", NOTEBOOKS, ids=lambda r: r.name)
def test_sin_datos_de_la_cuenta_de_colab(ruta):
    """Colab guarda en cada celda el nombre y el identificador de quien la ejecutó."""
    texto = ruta.read_text(encoding="utf-8")
    for clave in ('"executionInfo"', '"userId"', '"displayName"'):
        assert clave not in texto


PRINCIPALES = ["01_exploracion", "02_preprocesamiento", "03_modelado", "04_optimizacion", "05_evaluacion"]


@pytest.mark.parametrize("nombre", PRINCIPALES)
def test_notebooks_principales_ejecutados_sin_errores(nombre):
    cuaderno = nbformat.read(RAIZ / "notebooks" / f"{nombre}.ipynb", as_version=4)
    codigo = [c for c in cuaderno.cells if c.cell_type == "code"]
    assert all(c.get("execution_count") for c in codigo), "Hay celdas sin ejecutar"
    assert not any(o.get("output_type") == "error" for c in codigo for o in c.get("outputs", []))
