# Resultados

Figuras, métricas y reportes generados por los notebooks y por las pruebas de integración. Ningún
archivo de esta carpeta contiene texto de correos, claves ni indicadores vivos.

## Figuras (`figures/`)

| Carpeta | Figuras | Generadas por |
|---|---|---|
| `01_exploracion/` | 1 a 9: clase por corpus, longitud, URL, año, idioma, duplicados, correlaciones, términos por clase y datos en español | `notebooks/01_exploracion.ipynb` |
| `02_preprocesamiento/` | 10 y 11: exclusiones y particiones | `notebooks/02_preprocesamiento.ipynb` |
| `03_modelado/` | 12 a 16: coeficientes de la línea base, importancia de la rama URL, entrenamiento de DistilBERT, variantes de fusión y comparación en validación | `notebooks/03_modelado.ipynb` |
| `04_optimizacion/` | 17 (rama URL) y 18 (línea base) en seis vistas cada una: historial, importancia, *slice*, dependencia parcial, contorno y dependencia parcial 2D; 19: antes y después | `notebooks/04_optimizacion.ipynb` |
| `05_evaluacion/` | 20 a 26: matriz de confusión, curvas ROC y precisión-recall, calibración, riesgo por clase, sensibilidad al umbral, subgrupos y escenarios de estrés | `notebooks/05_evaluacion.ipynb` |
| `semana3/` | Diagnóstico de sobreajuste y subajuste de la Semana 3 | `notebooks/experimentos/16_diagnostico_sobreajuste.ipynb` |

## Métricas (`metrics/`)

**Resúmenes de los notebooks principales**

| Archivo | Contenido |
|---|---|
| `eda_resumen.json` | Tamaños, URL por clase, calidad, años, términos y balance |
| `preprocesamiento_resumen.json` | Reglas, exclusiones, particiones, pliegues, reproducibilidad y marcadores |
| `modelado_resumen.json` | Validación de cada componente, búsqueda de C, rama URL, DistilBERT y variantes de fusión |
| `optimizacion_resumen.json`, `optimizacion_pruebas_url.csv`, `optimizacion_pruebas_baseline.csv` | Workshop 2 de la Semana 5: configuraciones, importancias, comparación antes y después y cada prueba de Optuna |
| `evaluacion_final.json` | Prueba con intervalos de confianza, McNemar, áreas, calibración, subgrupos, ruta española, escenarios de estrés y metas SMART |
| `validacion_externa_mta.json` | Cuatro correos reales de phishing analizados con la interfaz |
| `demo_nube_v1.json` | Verificación de la demostración pública en Streamlit Community Cloud (22/10/2026) |

**Registros de los experimentos** (`notebooks/experimentos/`)

| Archivo | Contenido |
|---|---|
| `baseline_v1.json`, `rama_url_v1.json` | Línea base y rama URL (Sprint 2) |
| `distilbert_v1_*.json` | DistilBERT: entrenamiento principal, pliegues fuera de distribución y resumen |
| `fusion_v1.json` | Variantes de fusión en prueba y en los pliegues fuera de distribución |
| `inferencia_v1.json`, `despliegue_v1.json`, `bilingue_v1.json` | Fidelidad de la inferencia empaquetada, prueba de la API desde el Hub y validación bilingüe |
| `datos_es_v1.json`, `spam_es_v1.json`, `multilingue_*.json`, `fusion_es_v1.json` | Ruta española: datos, traducción, experimentos E0 a E2 y fusión |
| `fpr_enron_v1.json` | Falsos positivos en correo corporativo y elección del umbral operativo |
| `semana3/` | Curvas y comparaciones del diagnóstico de sobreajuste |

**Integración (`metrics/kpi/`)**

| Archivo | Contenido |
|---|---|
| `kpi_resumen.json`, `kpi_resultados.csv` | Lote de 200 correos por el flujo n8n: alertas integradas, eventos en Wazuh y latencia de extremo a extremo |
| `triaje_resumen.json`, `triaje_registros.csv` | Cronometraje del triaje manual frente al asistido (diseño cruzado, 40 registros) |

## Reportes (`reports/`)

| Archivo | Contenido |
|---|---|
| `resumen_resultados.md` | Resumen de la evaluación final, generado a partir de los archivos de `metrics/` |
