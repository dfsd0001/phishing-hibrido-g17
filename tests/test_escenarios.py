"""Pruebas de los escenarios de estrés del Workshop 1."""

import numpy as np
import pytest

from src import escenarios

TEXTO = "please verify your account password at __url__ or write to __email__ today"


def test_ruido_es_reproducible_con_la_misma_semilla():
    a = escenarios.ruido_caracteres(TEXTO, 0.2, np.random.default_rng(3))
    b = escenarios.ruido_caracteres(TEXTO, 0.2, np.random.default_rng(3))
    assert a == b
    assert a != TEXTO


def test_ruido_no_altera_los_marcadores():
    perturbado = escenarios.ruido_caracteres(TEXTO, 1.0, np.random.default_rng(0))
    assert "__url__" in perturbado
    assert "__email__" in perturbado


def test_ruido_cero_devuelve_el_mismo_texto():
    assert escenarios.ruido_caracteres(TEXTO, 0.0, np.random.default_rng(0)) == TEXTO


def test_ruido_rechaza_tasa_invalida():
    with pytest.raises(ValueError):
        escenarios.ruido_caracteres(TEXTO, 1.5, np.random.default_rng(0))


def test_tasa_de_ruido_aproximada():
    texto = "a" * 20000
    perturbado = escenarios.ruido_caracteres(texto, 0.1, np.random.default_rng(1))
    cambios = sum(c != "a" for c in perturbado) + abs(len(perturbado) - len(texto))
    assert 0.03 < cambios / len(texto) < 0.12


def test_ofuscacion_de_palabras_sensibles():
    resultado = escenarios.ofuscar_palabras_sensibles("Verify your PASSWORD now, see you at the meeting")
    assert resultado == "V3r1fy your P@55W0RD now, see you at the meeting"


def test_ofuscacion_en_espanol():
    assert escenarios.ofuscar_palabras_sensibles("confirme su contraseña") == "confirme su c0ntr@53ñ@"


def test_quitar_enlaces_y_truncar():
    assert "__url__" not in escenarios.quitar_enlaces(TEXTO)
    assert escenarios.truncar(TEXTO, 10) == TEXTO[:10]
    with pytest.raises(ValueError):
        escenarios.truncar(TEXTO, -1)


def test_remuestreo_alcanza_la_prevalencia():
    y = np.array([2] * 50 + [0] * 300 + [1] * 300)
    indices = escenarios.remuestreo_prevalencia(y, 0.05, np.random.default_rng(0))
    assert (y[indices] == 2).sum() == 50
    assert abs((y[indices] == 2).mean() - 0.05) < 0.001


def test_remuestreo_rechaza_prevalencia_invalida():
    with pytest.raises(ValueError):
        escenarios.remuestreo_prevalencia(np.array([0, 2]), 1.0, np.random.default_rng(0))
