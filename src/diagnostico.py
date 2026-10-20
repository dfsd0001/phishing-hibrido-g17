"""Registro de métricas de entrenamiento y diagnóstico de sobreajuste y subajuste.

* ``RegistroMetricas`` guarda las métricas de cada evaluación de un ciclo de entrenamiento.
* ``diagnosticar`` aplica reglas cuantitativas (brecha, tendencia de la brecha y subida de la
  pérdida de validación) y devuelve una etiqueta con la evidencia que la sustenta.
* ``graficar_*`` genera figuras a 300 DPI para el informe.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

COLOR = {"train": "#1f4e9c", "val": "#d1495b", "ood": "#e6a700"}
DPI = 300


class RegistroMetricas:
    """Registra métricas por evaluación.

    Ejemplo:
        registro.log(epoca=1, train_loss=0.3, val_loss=0.4, train_score=0.9, val_score=0.88)
    """

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.filas: list[dict] = []

    def log(self, **metricas) -> None:
        fila = {}
        for clave, valor in metricas.items():
            es_numero = isinstance(valor, (int, float, np.floating, np.integer))
            fila[clave] = float(valor) if es_numero else valor
        self.filas.append(fila)

    def df(self) -> pd.DataFrame:
        return pd.DataFrame(self.filas)

    def guardar(self, ruta: str | Path) -> None:
        Path(ruta).write_text(json.dumps({"nombre": self.nombre, "filas": self.filas}, indent=1))

    @classmethod
    def cargar(cls, ruta: str | Path) -> RegistroMetricas:
        datos = json.loads(Path(ruta).read_text())
        registro = cls(datos["nombre"])
        registro.filas = datos["filas"]
        return registro


def _pendiente(valores) -> float:
    valores = np.asarray(valores, float)
    if len(valores) < 2:
        return 0.0
    return float(np.polyfit(np.arange(len(valores)), valores, 1)[0])


def diagnosticar(
    historial: pd.DataFrame,
    x: str = "epoca",
    umbral_score_bajo: float = 0.85,
    umbral_gap: float = 0.03,
    umbral_subida_val: float = 0.10,
) -> dict:
    """Diagnostica un historial con ``train_loss``, ``val_loss``, ``train_score`` y ``val_score``.

    Reglas:
        * Sobreajuste: la pérdida de validación sube más de ``umbral_subida_val`` sobre su
          mínimo mientras la de entrenamiento baja, o la brecha de puntaje final supera
          ``umbral_gap`` con tendencia creciente de la brecha de pérdida.
        * Subajuste: puntaje de entrenamiento final menor que ``umbral_score_bajo``.
        * Óptimo: brecha pequeña y estable.
        * Si existe ``ood_score`` (fuente no vista) y el modelo es óptimo en su distribución
          pero cae más de 0,20 fuera de ella: sobreajuste a la fuente.
    """
    d = historial.sort_values(x).reset_index(drop=True)
    tl, vl, ts, vs = (d[c].to_numpy(float) for c in ("train_loss", "val_loss", "train_score", "val_score"))
    i_min = int(np.argmin(vl))
    gap_loss, gap_score = vl - tl, ts - vs
    mitad = len(d) // 2
    m = {
        "evaluaciones": int(len(d)),
        "train_loss_final": round(tl[-1], 5),
        "val_loss_final": round(vl[-1], 5),
        "train_score_final": round(ts[-1], 4),
        "val_score_final": round(vs[-1], 4),
        "gap_loss_final": round(gap_loss[-1], 5),
        "gap_score_final": round(gap_score[-1], 4),
        "pendiente_gap_loss_2a_mitad": round(_pendiente(gap_loss[mitad:]), 6),
        "val_loss_min": round(vl[i_min], 5),
        f"{x}_val_loss_min": float(d.loc[i_min, x]),
        "subida_val_loss_sobre_min_rel": round((vl[-1] - vl[i_min]) / max(vl[i_min], 1e-9), 4),
        "train_loss_baja_tras_min": bool(tl[-1] < tl[i_min]),
    }
    if "ood_score" in d:
        ood = d["ood_score"].to_numpy(float)
        j = int(np.argmax(ood))
        m.update(
            {
                "ood_score_final": round(ood[-1], 4),
                "ood_score_max": round(ood[j], 4),
                f"{x}_ood_max": float(d.loc[j, x]),
                "gap_val_ood_final": round(vs[-1] - ood[-1], 4),
                "caida_ood_desde_max": round(ood[j] - ood[-1], 4),
            }
        )
    c1 = m["subida_val_loss_sobre_min_rel"] > umbral_subida_val and m["train_loss_baja_tras_min"]
    c2 = m["gap_score_final"] > umbral_gap and m["pendiente_gap_loss_2a_mitad"] > 0
    c3 = m["train_score_final"] < umbral_score_bajo
    m["criterios"] = {
        "val_loss_sube_y_train_baja": bool(c1),
        "gap_score_alto_y_creciente": bool(c2),
        "train_score_bajo": bool(c3),
    }
    if c3:
        m["diagnostico"] = "underfitting"
    elif c1 or c2:
        m["diagnostico"] = "overfitting"
    else:
        m["diagnostico"] = "optimo"
    if "ood_score" in d and m["diagnostico"] == "optimo" and m["gap_val_ood_final"] > 0.20:
        m["diagnostico"] = "optimo_en_distribucion_overfitting_a_fuente"
    return m


def _etiqueta_eje(x: str) -> str:
    return {"epoca": "Época", "paso": "Paso"}.get(x, x.capitalize())


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _formato_ejes(ax, titulo: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(titulo, fontsize=11, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.35, linestyle="--")
    ax.legend(frameon=True, fontsize=8)


def graficar_entrenamiento(historial, titulo, ruta, x="epoca", score_label="F1 macro") -> None:
    """Dos paneles: pérdida y puntaje de entrenamiento frente a validación (y fuente no vista)."""
    plt = _pyplot()
    d = historial.sort_values(x).reset_index(drop=True)
    fig, (ax_loss, ax_score) = plt.subplots(1, 2, figsize=(11, 4.2))

    ax_loss.plot(d[x], d["train_loss"], "o-", color=COLOR["train"], label="Entrenamiento")
    ax_loss.plot(d[x], d["val_loss"], "s-", color=COLOR["val"], label="Validación")
    i = int(d["val_loss"].idxmin())
    ax_loss.scatter([d.loc[i, x]], [d.loc[i, "val_loss"]], s=140, facecolors="none", edgecolors="black", zorder=5)
    ax_loss.annotate(
        f"mín. val loss {d.loc[i, 'val_loss']:.3f}\n({x} {d.loc[i, x]:g})",
        (d.loc[i, x], d.loc[i, "val_loss"]),
        textcoords="offset points",
        xytext=(10, 18),
        fontsize=8,
        arrowprops={"arrowstyle": "->"},
    )
    _formato_ejes(ax_loss, "A. Pérdida (entropía cruzada)", _etiqueta_eje(x), "Loss")

    ax_score.plot(d[x], d["train_score"], "o-", color=COLOR["train"], label="Entrenamiento")
    ax_score.plot(d[x], d["val_score"], "s-", color=COLOR["val"], label="Validación (misma distribución)")
    if "ood_score" in d:
        ax_score.plot(d[x], d["ood_score"], "^-", color=COLOR["ood"], label="Fuente no vista (recall de phishing)")
        u = len(d) - 1
        ax_score.annotate(
            f"brecha validación - fuente no vista: {d.loc[u, 'val_score'] - d.loc[u, 'ood_score']:.2f}",
            (d.loc[u, x], d.loc[u, "ood_score"]),
            textcoords="offset points",
            xytext=(-150, 25),
            fontsize=8,
            arrowprops={"arrowstyle": "->"},
        )
    _formato_ejes(ax_score, f"B. {score_label}", _etiqueta_eje(x), "Puntaje")

    fig.suptitle(titulo, fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ruta, dpi=DPI)
    plt.close(fig)


def _curva_con_banda(ax, x, curvas, log_x: bool = False) -> None:
    for valores, color, etiqueta in curvas:
        media, desviacion = np.mean(valores, 1), np.std(valores, 1)
        trazar = ax.semilogx if log_x else ax.plot
        trazar(x, media, "o-", color=color, label=etiqueta)
        ax.fill_between(x, media - desviacion, media + desviacion, color=color, alpha=0.15)


def graficar_learning_curve(tamanos, train, val, titulo, ruta, score_label="F1 macro") -> None:
    """Curva de aprendizaje por tamaño de entrenamiento: media y desviación entre folds."""
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    _curva_con_banda(ax, tamanos, [(train, COLOR["train"], "Entrenamiento"), (val, COLOR["val"], "Validación cruzada")])
    brecha = np.mean(train, 1)[-1] - np.mean(val, 1)[-1]
    ax.annotate(
        f"brecha final: {brecha:.3f}",
        (tamanos[-1], np.mean(val, 1)[-1]),
        textcoords="offset points",
        xytext=(-80, -28),
        fontsize=8,
        arrowprops={"arrowstyle": "->"},
    )
    _formato_ejes(ax, titulo, "Correos de entrenamiento", score_label)
    fig.tight_layout()
    fig.savefig(ruta, dpi=DPI)
    plt.close(fig)


def graficar_validation_curve(valores, train, val, titulo, ruta, param="C", score_label="F1 macro") -> None:
    """Curva de validación por hiperparámetro en escala logarítmica, con el óptimo marcado."""
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    _curva_con_banda(
        ax,
        valores,
        [(train, COLOR["train"], "Entrenamiento"), (val, COLOR["val"], "Validación cruzada")],
        log_x=True,
    )
    k = int(np.argmax(np.mean(val, 1)))
    ax.axvline(valores[k], color="black", linestyle=":", linewidth=1)
    ax.annotate(
        f"óptimo {param}={valores[k]:g}",
        (valores[k], np.mean(val, 1)[k]),
        textcoords="offset points",
        xytext=(12, -30),
        fontsize=8,
        arrowprops={"arrowstyle": "->"},
    )
    ax.text(0.02, 0.03, "más regularización", transform=ax.transAxes, fontsize=7, color="gray")
    ax.text(0.98, 0.03, "menos regularización", transform=ax.transAxes, fontsize=7, color="gray", ha="right")
    _formato_ejes(ax, titulo, f"{param} (escala log)", score_label)
    fig.tight_layout()
    fig.savefig(ruta, dpi=DPI)
    plt.close(fig)


def graficar_comparacion(antes, despues, titulo, ruta, x="epoca", col="val_loss", etiqueta="Val loss") -> None:
    """Compara la misma métrica antes y después de aplicar las estrategias de mejora."""
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(antes[x], antes[col], "s--", color=COLOR["val"], label="Modelo base")
    ax.plot(despues[x], despues[col], "o-", color=COLOR["train"], label="Con estrategias de mejora")
    _formato_ejes(ax, titulo, _etiqueta_eje(x), etiqueta)
    fig.tight_layout()
    fig.savefig(ruta, dpi=DPI)
    plt.close(fig)
