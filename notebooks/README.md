# Notebooks

Los cinco notebooks de esta carpeta siguen la estructura de la entrega y resumen el trabajo de
`notebooks/experimentos/`, que conserva el registro completo y ejecutado del desarrollo. Todos
importan el código de `src/` y leen la configuración de `config.yaml`, de modo que no repiten
lógica ni valores.

| Notebook | Contenido | Escribe en `results/` | Entorno | Tiempo aproximado |
|---|---|---|---|---|
| `01_exploracion` | Análisis exploratorio: composición por corpus, longitud, URL, años, idioma, duplicados, correlaciones, términos por clase, datos en español | `figures/01_exploracion`, `metrics/eda_resumen.json` | CPU | 5 min |
| `02_preprocesamiento` | Defanging, exclusiones, texto de modelo, particiones, pliegues fuera de distribución, reproducibilidad del dataset y controles de fuga | `figures/02_preprocesamiento`, `metrics/preprocesamiento_resumen.json` | CPU | 10 min |
| `03_modelado` | Piso de referencia, línea base, rama URL, DistilBERT y variantes de fusión, solo con entrenamiento y validación | `figures/03_modelado`, `metrics/modelado_resumen.json` | CPU | 15 min |
| `04_optimizacion` | Workshop 2 de la Semana 5: Optuna, importancia de hiperparámetros, dependencia parcial, interacciones y comparación antes y después | `figures/04_optimizacion`, `metrics/optimizacion_*` | CPU | 60 min como máximo |
| `05_evaluacion` | Prueba final con intervalos de confianza, McNemar, curvas, calibración, subgrupos, Workshop 1 (escenarios de estrés), ruta española y metas SMART | `figures/05_evaluacion`, `metrics/evaluacion_final.json` | GPU recomendada | 20 min |

El análisis por subgrupos de `05_evaluacion` se ejecutó en Colab con fairlearn 0.13.0. El
`requirements.txt` fija la 0.14.0 porque la 0.13.0 exige SciPy anterior a 1.16 y choca con la versión
que usa la API (1.16.3); con datos de control, `MetricFrame` produce resultados idénticos en ambas.

Los tiempos son estimaciones para Google Colab; los límites de la búsqueda de hiperparámetros
están en la sección `optimizacion` de `config.yaml`.

## Datos y modelos que necesitan

Los notebooks no descargan datos: leen las tablas y artefactos generados por
`notebooks/experimentos/`, que se describen en `data/README.md` y `models/README.md`.

| Ruta (relativa a la carpeta de datos) | Origen |
|---|---|
| `data/interim/emails_v0.parquet` | `experimentos/02_eda_dqr` |
| `data/eda/dqr_v1.json` | `experimentos/02_eda_dqr` |
| `data/processed/emails_v1.parquet` | `experimentos/03_preparacion_splits` |
| `data/processed/url_scores_v1.parquet` | `experimentos/04_rama_url` |
| `data/processed/text_scores_distilbert_v1.parquet` | `experimentos/06_distilbert` |
| `data/processed/emails_es_v2.parquet` | `experimentos/10_datos_es` y `10b_spam_es_traduccion` |
| `data/processed/text_scores_multi_es_v1.parquet` | `experimentos/11_distilbert_multilingue` |
| `models/` | Artefactos publicados (versión v2 en Hugging Face Hub) |

## Ejecución

**Google Colab.** Copiar el repositorio a `MyDrive/PI_G17/phishing-hibrido-g17` y tener los datos
en `MyDrive/PI_G17` (la estructura de la tabla anterior). Cada notebook monta Drive en su primera
celda. Para `05_evaluacion`, elegir un entorno con GPU.

**Local.** Desde la carpeta `notebooks/`, con el entorno de `requirements.txt` y la variable
`G17_BASE` apuntando a la carpeta que contiene `data/` y `models/`:

```bash
export G17_BASE=/ruta/a/PI_G17
jupyter lab
```
