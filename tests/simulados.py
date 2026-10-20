"""Componentes simulados del detector para pruebas sin GPU, sin red y sin artefactos reales.

Reproducen la interfaz de los modelos reales con reglas simples. Las pruebas con los modelos
publicados se hicieron en Colab (notebooks 08 y 13 de ``notebooks/experimentos``).
"""

import json
from pathlib import Path

import jsonschema
import numpy as np
from sklearn.linear_model import LogisticRegression

from src.model import Detector

RAIZ = Path(__file__).resolve().parents[1]
ESQUEMA = json.loads((RAIZ / "contracts" / "contrato_v1.schema.json").read_text(encoding="utf-8"))
VALIDADOR = jsonschema.Draft202012Validator(ESQUEMA, format_checker=jsonschema.FormatChecker())
TLD = ["com", "net", "__otro__"]

CORREOS = {
    "phishing": (
        "Account suspended",
        "Dear user, verify your password at https://secure-login.example.com/verify?id=7 or 192.0.2.4 today.",
    ),
    "legitimo": ("Reunión", "Hola equipo, nos vemos el martes para revisar el informe."),
    "spam": ("Oferta", "Gran oferta de relojes, visita www.tienda.example.net/promo"),
}


class TextoSimulado:
    """P(phishing) alta con palabras de credenciales; spam con la palabra 'oferta'."""

    def __call__(self, texto: str) -> np.ndarray:
        texto = texto.lower()
        if "password" in texto or "verify" in texto:
            return np.array([0.02, 0.03, 0.95])
        if "oferta" in texto:
            return np.array([0.05, 0.9, 0.05])
        return np.array([0.9, 0.08, 0.02])


class TextoSimuladoEspanol:
    def __call__(self, texto: str) -> np.ndarray:
        texto = texto.lower()
        if "contraseña" in texto or "verifique" in texto:
            return np.array([0.03, 0.02, 0.95])
        if "oferta" in texto:
            return np.array([0.05, 0.90, 0.05])
        return np.array([0.92, 0.06, 0.02])


class BaselineSimulado:
    def predict_proba(self, textos):
        return np.vstack([TextoSimulado()(t) for t in textos])


class UrlSimulada:
    def predict_proba(self, X):
        puntaje = np.clip(0.2 + 0.3 * X["n_palabras_sensibles"].values + 0.3 * X["tiene_arroba"].values, 0, 1)
        return np.c_[1 - puntaje, puntaje]


class MetaEspanolSimulado:
    """Meta-clasificador binario: P(phishing) igual a la del texto."""

    def predict_proba(self, X):
        p = np.exp(X[:, 2])
        return np.c_[1 - p, p]


def meta_entrenado() -> LogisticRegression:
    """Meta-clasificador de la variante V3 ajustado sobre datos sintéticos coherentes."""
    generador = np.random.RandomState(0)
    y = generador.randint(0, 3, 600)
    probabilidades = generador.dirichlet([1, 1, 1], 600) * 0.3
    probabilidades[np.arange(600), y] += 0.7
    X = np.c_[
        np.log(probabilidades),
        np.log(probabilidades),
        generador.rand(600, 2),
        generador.rand(600) < 0.3,
        generador.rand(600),
    ]
    return LogisticRegression(max_iter=2000).fit(X, y)


def detector_ingles() -> Detector:
    return Detector(TextoSimulado(), BaselineSimulado(), UrlSimulada(), TLD, meta_entrenado(), 0.5, "V3")


def detector_bilingue() -> Detector:
    espanol = {"texto_fn": TextoSimuladoEspanol(), "meta": MetaEspanolSimulado(), "umbral": 0.5, "variante": "V1_es"}
    return Detector(TextoSimulado(), BaselineSimulado(), UrlSimulada(), TLD, meta_entrenado(), 0.5, "V3", es=espanol)
