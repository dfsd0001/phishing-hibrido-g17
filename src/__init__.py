"""Detección y clasificación híbrida de phishing (texto + URL).

Paquete del Proyecto Integrador MIAR0545 (Maestría en Inteligencia Artificial, UEES), Grupo 17.

Módulos:
    ioc_utils        Extracción, defanging y refanging de indicadores (URL, IPv4).
    url_features     Variables léxicas calculadas solo a partir de la cadena de la URL.
    data_processing  Lectura de correos, normalización y texto de entrada de los modelos.
    model            Detector de producción: fusión tardía de las ramas y contrato JSON.
    train            Entrenamiento reproducible de la línea base y de la rama URL.
    evaluate         Métricas, umbrales, calibración e intervalos de confianza.
    diagnostico      Registro de métricas y diagnóstico de sobreajuste (Semana 3).
    utils            Configuración, semillas, registro de eventos y rutas.
"""

__version__ = "1.0.0"
