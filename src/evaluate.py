"""Métricas de evaluación, selección de umbrales, calibración e incertidumbre estadística.

Convención de clases: 0 = legítimo, 1 = spam, 2 = phishing. El phishing es la clase
positiva para recall, FPR y calibración.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import binomtest, norm
from sklearn.metrics import f1_score, precision_recall_fscore_support, roc_curve

CLASES = ["legitimo", "spam", "phishing"]
PH = 2


def predecir(probabilidades: np.ndarray, umbral: float) -> np.ndarray:
    """Asigna phishing si P(phishing) >= umbral; en otro caso, la mayor entre legítimo y spam."""
    prediccion = probabilidades[:, :2].argmax(1)
    prediccion[probabilidades[:, PH] >= umbral] = PH
    return prediccion


def metricas(y: np.ndarray, prediccion: np.ndarray) -> dict:
    """F1 macro, precisión y recall por clase, y tasas de falsos positivos de phishing.

    ``fpr_phishing`` cuenta como error cualquier correo no phishing marcado como phishing;
    ``fpr_legitimo_a_phishing`` se limita a los legítimos.
    """
    y = np.asarray(y)
    prediccion = np.asarray(prediccion)
    precision, recall, _, _ = precision_recall_fscore_support(y, prediccion, labels=[0, 1, 2], zero_division=0)
    no_phishing = y != PH
    legitimo = y == 0
    return {
        "f1_macro": round(float(f1_score(y, prediccion, average="macro", labels=[0, 1, 2], zero_division=0)), 4),
        "precision": dict(zip(CLASES, np.round(precision, 4).tolist(), strict=True)),
        "recall": dict(zip(CLASES, np.round(recall, 4).tolist(), strict=True)),
        "fpr_phishing": round(float((prediccion[no_phishing] == PH).mean()), 4) if no_phishing.any() else None,
        "fpr_legitimo_a_phishing": round(float((prediccion[legitimo] == PH).mean()), 4) if legitimo.any() else None,
        "n": int(len(y)),
    }


def umbral_por_fpr(y: np.ndarray, p_phishing: np.ndarray, fpr_max: float = 0.01) -> float:
    """Umbral más bajo (máximo recall) cuyo FPR en el conjunto dado no supera ``fpr_max``.

    Se calcula siempre sobre validación, nunca sobre el conjunto de prueba.
    """
    negativos = np.sort(np.asarray(p_phishing)[np.asarray(y) != PH])[::-1]
    k = int(np.floor(fpr_max * len(negativos)))
    return float(np.nextafter(negativos[k], 1)) if k < len(negativos) else 0.0


def umbral_para_recall(y: np.ndarray, p_phishing: np.ndarray, objetivo: float = 0.95) -> float:
    """Umbral más alto sobre P(phishing) que alcanza el recall objetivo en el conjunto dado."""
    positivos = np.sort(np.asarray(p_phishing)[np.asarray(y) == PH])[::-1]
    if not len(positivos):
        return 0.5
    return float(positivos[min(int(np.ceil(objetivo * len(positivos))) - 1, len(positivos) - 1)])


def tpr_a_fpr(y_binaria: np.ndarray, puntajes: np.ndarray, fpr_max: float) -> tuple[float, float]:
    """Mayor TPR alcanzable con FPR <= ``fpr_max`` y el umbral correspondiente (caso binario)."""
    fpr, tpr, umbrales = roc_curve(y_binaria, puntajes)
    i = np.where(fpr <= fpr_max)[0][-1]
    return float(tpr[i]), float(umbrales[i])


def brier(y: np.ndarray, probabilidades: np.ndarray) -> float:
    """Puntaje de Brier multiclase (menor es mejor)."""
    one_hot = np.eye(probabilidades.shape[1])[np.asarray(y)]
    return round(float(np.mean(np.sum((probabilidades - one_hot) ** 2, 1))), 5)


def ece_phishing(y: np.ndarray, p_phishing: np.ndarray, n_bins: int = 10) -> float:
    """Error de calibración esperado (ECE) de P(phishing) con contenedores de igual ancho."""
    y_binaria = (np.asarray(y) == PH).astype(float)
    p_phishing = np.asarray(p_phishing, dtype=float)
    error = 0.0
    bordes = np.linspace(0, 1, n_bins + 1)
    for i in range(n_bins):
        if i < n_bins - 1:
            mascara = (p_phishing >= bordes[i]) & (p_phishing < bordes[i + 1])
        else:
            mascara = p_phishing >= bordes[i]
        if mascara.any():
            error += mascara.mean() * abs(y_binaria[mascara].mean() - p_phishing[mascara].mean())
    return round(float(error), 5)


def intervalo_wilson(exitos: int, n: int, confianza: float = 0.95) -> tuple[float, float]:
    """Intervalo de Wilson para una proporción (adecuado con proporciones cercanas a 0 o 1)."""
    if n == 0:
        return 0.0, 1.0
    z = norm.ppf(1 - (1 - confianza) / 2)
    p = exitos / n
    denominador = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / denominador
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominador
    return max(0.0, centro - margen), min(1.0, centro + margen)


def intervalo_bootstrap(
    y: np.ndarray,
    prediccion: np.ndarray,
    metrica,
    n_remuestreos: int = 2000,
    confianza: float = 0.95,
    semilla: int = 17,
) -> tuple[float, float, float]:
    """Estimación puntual e intervalo bootstrap por percentiles de una métrica.

    Args:
        metrica: Función ``f(y, prediccion) -> float``.

    Returns:
        Tupla (valor, límite inferior, límite superior).
    """
    y = np.asarray(y)
    prediccion = np.asarray(prediccion)
    generador = np.random.default_rng(semilla)
    n = len(y)
    valores = []
    for _ in range(n_remuestreos):
        indices = generador.integers(0, n, n)
        valores.append(metrica(y[indices], prediccion[indices]))
    alfa = (1 - confianza) / 2
    inferior, superior = np.percentile(valores, [100 * alfa, 100 * (1 - alfa)])
    return float(metrica(y, prediccion)), float(inferior), float(superior)


def prueba_mcnemar(y: np.ndarray, prediccion_a: np.ndarray, prediccion_b: np.ndarray) -> dict:
    """Prueba exacta de McNemar entre dos clasificadores evaluados sobre los mismos casos.

    Returns:
        Diccionario con los casos discordantes (``solo_a`` acierta A y falla B; ``solo_b`` al
        revés) y el valor p bilateral.
    """
    y = np.asarray(y)
    acierta_a = np.asarray(prediccion_a) == y
    acierta_b = np.asarray(prediccion_b) == y
    solo_a = int(np.sum(acierta_a & ~acierta_b))
    solo_b = int(np.sum(~acierta_a & acierta_b))
    discordantes = solo_a + solo_b
    p_valor = 1.0 if discordantes == 0 else float(binomtest(solo_a, discordantes, 0.5).pvalue)
    return {"solo_a": solo_a, "solo_b": solo_b, "p_valor": round(p_valor, 6)}
