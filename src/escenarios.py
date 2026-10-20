"""Escenarios de estrés para validar el detector en condiciones simuladas.

Implementa las perturbaciones del Workshop 1 de la Semana 5 adaptadas a correo electrónico.
Cada función recibe un texto de modelo (ya defangeado y con marcadores, ver
``data_processing.texto_para_modelo``) y devuelve una versión perturbada. Los marcadores
(``__url__``, ``__email__``, etc.) nunca se alteran, porque los produce el propio sistema y
no el remitente.

Escenarios:

* Ruido: errores tipográficos aleatorios en las letras.
* Ofuscación: sustitución de letras por números o símbolos en palabras típicas de phishing,
  una técnica conocida de evasión de filtros.
* Información incompleta: texto truncado o sin enlaces.
* Desbalance: cambio de la prevalencia de phishing sin cambiar el modelo.
"""

from __future__ import annotations

import re

import numpy as np

LETRAS = "abcdefghijklmnopqrstuvwxyz"
_MARCADOR = re.compile(r"__[a-z_]+__")
_ESPACIOS = re.compile(r"\s+")

SUSTITUCIONES = {"a": "@", "e": "3", "i": "1", "o": "0", "s": "5"}
PALABRAS_SENSIBLES = (
    "account",
    "password",
    "verify",
    "verification",
    "login",
    "update",
    "confirm",
    "security",
    "bank",
    "suspended",
    "unusual",
    "click",
    "urgent",
    "invoice",
    "payment",
    "credentials",
    "cuenta",
    "contraseña",
    "verificar",
    "seguridad",
    "banco",
    "pago",
    "factura",
    "urgente",
)
_PALABRAS = re.compile(r"(?i)\b(" + "|".join(PALABRAS_SENSIBLES) + r")\b")


def _posiciones_protegidas(texto: str) -> np.ndarray:
    """Máscara de los caracteres que pertenecen a un marcador."""
    protegidas = np.zeros(len(texto), dtype=bool)
    for coincidencia in _MARCADOR.finditer(texto):
        protegidas[coincidencia.start() : coincidencia.end()] = True
    return protegidas


def ruido_caracteres(texto: str, tasa: float, generador: np.random.Generator) -> str:
    """Introduce errores tipográficos: cada letra se altera con probabilidad ``tasa``.

    La alteración es, con igual probabilidad, sustituir la letra por otra al azar,
    eliminarla o duplicarla.

    Args:
        texto: Texto de modelo.
        tasa: Probabilidad de alterar cada letra, entre 0 y 1.
        generador: Generador de NumPy con semilla fija, para que el escenario sea reproducible.
    """
    if not 0 <= tasa <= 1:
        raise ValueError("La tasa de ruido debe estar entre 0 y 1")
    if not texto or tasa == 0:
        return texto
    protegidas = _posiciones_protegidas(texto)
    sorteo = generador.random(len(texto))
    operacion = generador.integers(0, 3, len(texto))
    reemplazo = generador.integers(0, len(LETRAS), len(texto))
    salida = []
    for i, caracter in enumerate(texto):
        if protegidas[i] or not caracter.isalpha() or sorteo[i] >= tasa:
            salida.append(caracter)
        elif operacion[i] == 0:
            salida.append(LETRAS[reemplazo[i]])
        elif operacion[i] == 2:
            salida.append(caracter * 2)
    return "".join(salida)


def ofuscar_palabras_sensibles(texto: str) -> str:
    """Reemplaza letras por números o símbolos en palabras típicas de phishing.

    Por ejemplo, ``password`` pasa a ``p@55w0rd``. Simula a un atacante que intenta evadir
    filtros basados en palabras clave. El resto del texto no cambia.
    """

    def ofuscar(coincidencia: re.Match) -> str:
        return "".join(SUSTITUCIONES.get(c.lower(), c) for c in coincidencia.group(0))

    return _PALABRAS.sub(ofuscar, texto)


def truncar(texto: str, max_caracteres: int) -> str:
    """Conserva solo los primeros ``max_caracteres`` (correo incompleto o vista previa)."""
    if max_caracteres < 0:
        raise ValueError("max_caracteres no puede ser negativo")
    return texto[:max_caracteres]


def quitar_enlaces(texto: str) -> str:
    """Elimina los marcadores de URL del texto (correo sin enlaces, por ejemplo con un QR)."""
    return _ESPACIOS.sub(" ", texto.replace("__url__", " ")).strip()


def remuestreo_prevalencia(
    y: np.ndarray,
    prevalencia: float,
    generador: np.random.Generator,
    clase_positiva: int = 2,
) -> np.ndarray:
    """Índices de una muestra con la prevalencia de phishing indicada.

    Conserva todos los casos positivos y toma los negativos con reemplazo hasta alcanzar la
    proporción objetivo. El modelo no cambia; cambia la población donde se usa.
    """
    if not 0 < prevalencia < 1:
        raise ValueError("La prevalencia debe estar entre 0 y 1, sin incluirlos")
    y = np.asarray(y)
    positivos = np.flatnonzero(y == clase_positiva)
    negativos = np.flatnonzero(y != clase_positiva)
    n_negativos = int(round(len(positivos) * (1 - prevalencia) / prevalencia))
    return np.concatenate([positivos, generador.choice(negativos, n_negativos, replace=True)])
