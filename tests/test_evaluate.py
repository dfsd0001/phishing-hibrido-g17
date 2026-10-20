"""Pruebas de métricas, umbrales, calibración e intervalos de confianza."""

import numpy as np
import pytest
from sklearn.metrics import f1_score

from src.evaluate import (
    brier,
    ece_phishing,
    intervalo_bootstrap,
    intervalo_wilson,
    metricas,
    predecir,
    prueba_mcnemar,
    umbral_para_recall,
    umbral_por_fpr,
)


def test_predecir_prioriza_phishing_sobre_el_umbral():
    probabilidades = np.array([[0.6, 0.1, 0.3], [0.2, 0.7, 0.1], [0.5, 0.1, 0.4]])
    assert predecir(probabilidades, 0.35).tolist() == [0, 1, 2]


def test_metricas_caso_perfecto():
    y = np.array([0, 1, 2, 2])
    resultado = metricas(y, y)
    assert resultado["f1_macro"] == 1.0
    assert resultado["fpr_phishing"] == 0.0
    assert resultado["recall"]["phishing"] == 1.0


def test_fpr_cuenta_solo_no_phishing():
    y = np.array([0, 0, 1, 1, 2])
    prediccion = np.array([2, 0, 1, 1, 2])
    resultado = metricas(y, prediccion)
    assert resultado["fpr_phishing"] == 0.25
    assert resultado["fpr_legitimo_a_phishing"] == 0.5


def test_umbral_por_fpr_respeta_el_maximo():
    generador = np.random.default_rng(0)
    y = np.r_[np.zeros(1000, int), np.full(200, 2)]
    p = np.r_[generador.uniform(0, 0.6, 1000), generador.uniform(0.4, 1, 200)]
    umbral = umbral_por_fpr(y, p, fpr_max=0.01)
    fpr = float((p[y != 2] >= umbral).mean())
    assert fpr <= 0.01


def test_umbral_para_recall_alcanza_el_objetivo():
    y = np.array([2] * 20 + [0] * 20)
    p = np.r_[np.linspace(0.5, 1.0, 20), np.linspace(0, 0.4, 20)]
    umbral = umbral_para_recall(y, p, objetivo=0.95)
    assert (p[y == 2] >= umbral).mean() >= 0.95


def test_brier_y_ece_de_un_modelo_perfecto():
    y = np.array([0, 1, 2])
    probabilidades = np.eye(3)
    assert brier(y, probabilidades) == 0.0
    assert ece_phishing(y, probabilidades[:, 2]) == 0.0


def test_intervalo_wilson_contiene_la_proporcion():
    inferior, superior = intervalo_wilson(9, 95)
    assert inferior < 9 / 95 < superior
    assert intervalo_wilson(0, 0) == (0.0, 1.0)


def test_intervalo_bootstrap_contiene_el_valor():
    generador = np.random.default_rng(1)
    y = generador.integers(0, 3, 300)
    prediccion = np.where(generador.random(300) < 0.8, y, (y + 1) % 3)

    def f1(y_, p_):
        return f1_score(y_, p_, average="macro")

    valor, inferior, superior = intervalo_bootstrap(y, prediccion, f1, n_remuestreos=300)
    assert inferior <= valor <= superior


def test_mcnemar_detecta_clasificadores_distintos():
    y = np.zeros(100, int)
    a = np.zeros(100, int)
    b = np.r_[np.zeros(60, int), np.ones(40, int)]
    resultado = prueba_mcnemar(y, a, b)
    assert resultado["solo_a"] == 40
    assert resultado["solo_b"] == 0
    assert resultado["p_valor"] < 0.001


def test_mcnemar_sin_discordancias():
    y = np.array([0, 1, 2])
    assert prueba_mcnemar(y, y, y)["p_valor"] == pytest.approx(1.0)
