"""Pruebas del diagnóstico de sobreajuste y de las figuras de entrenamiento."""

import numpy as np
import pandas as pd
import pytest

from src.diagnostico import (
    RegistroMetricas,
    diagnosticar,
    graficar_comparacion,
    graficar_entrenamiento,
    graficar_learning_curve,
    graficar_validation_curve,
)


def historial(train_loss, val_loss, train_score, val_score, ood=None):
    datos = pd.DataFrame(
        {
            "epoca": range(1, len(train_loss) + 1),
            "train_loss": train_loss,
            "val_loss": val_loss,
            "train_score": train_score,
            "val_score": val_score,
        }
    )
    if ood is not None:
        datos["ood_score"] = ood
    return datos


def test_sobreajuste():
    resultado = diagnosticar(
        historial(
            [0.6, 0.3, 0.1, 0.02, 0.005],
            [0.5, 0.35, 0.33, 0.40, 0.52],
            [0.8, 0.9, 0.97, 0.995, 1],
            [0.78, 0.86, 0.88, 0.87, 0.86],
        )
    )
    assert resultado["diagnostico"] == "overfitting"
    assert resultado["epoca_val_loss_min"] == 3


def test_subajuste():
    resultado = diagnosticar(
        historial([1.0, 0.98, 0.97, 0.96], [1.02, 1.0, 0.99, 0.99], [0.45, 0.48, 0.5, 0.51], [0.44, 0.47, 0.49, 0.5])
    )
    assert resultado["diagnostico"] == "underfitting"


def test_ajuste_optimo():
    resultado = diagnosticar(
        historial([0.5, 0.2, 0.12, 0.1], [0.52, 0.23, 0.15, 0.13], [0.85, 0.94, 0.96, 0.965], [0.84, 0.93, 0.95, 0.955])
    )
    assert resultado["diagnostico"] == "optimo"


def test_sobreajuste_a_la_fuente():
    resultado = diagnosticar(
        historial(
            [0.5, 0.2, 0.12, 0.1],
            [0.52, 0.23, 0.15, 0.13],
            [0.85, 0.94, 0.96, 0.965],
            [0.84, 0.93, 0.95, 0.955],
            ood=[0.6, 0.5, 0.4, 0.3],
        )
    )
    assert resultado["diagnostico"] == "optimo_en_distribucion_overfitting_a_fuente"
    assert resultado["caida_ood_desde_max"] == pytest.approx(0.3)


def test_registro_se_guarda_y_se_carga(tmp_path):
    registro = RegistroMetricas("prueba")
    registro.log(epoca=1, train_loss=np.float32(0.5))
    registro.guardar(tmp_path / "registro.json")
    cargado = RegistroMetricas.cargar(tmp_path / "registro.json")
    assert cargado.df().loc[0, "train_loss"] == pytest.approx(0.5)


def test_figuras_a_300_dpi(tmp_path):
    from PIL import Image

    datos = historial([0.6, 0.3, 0.1], [0.5, 0.35, 0.4], [0.8, 0.9, 0.97], [0.78, 0.86, 0.85], ood=[0.5, 0.4, 0.3])
    graficar_entrenamiento(datos, "t", tmp_path / "a.png")
    puntajes = np.random.RandomState(0).rand(4, 3)
    graficar_learning_curve([100, 200, 300, 400], puntajes, puntajes * 0.9, "t", tmp_path / "b.png")
    graficar_validation_curve([0.01, 0.1, 1, 10], puntajes, puntajes * 0.9, "t", tmp_path / "c.png")
    graficar_comparacion(datos, datos, "t", tmp_path / "d.png")
    for nombre in "abcd":
        assert round(Image.open(tmp_path / f"{nombre}.png").info["dpi"][0]) == 300
