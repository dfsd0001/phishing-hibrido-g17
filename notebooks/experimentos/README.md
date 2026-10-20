# Notebooks de experimentación

Registro completo y ejecutado del desarrollo del modelo, en el orden en que se construyó. Cada
notebook se ejecutó en Google Colab (GPU T4 cuando se indica) sobre los datos de Google Drive, y
conserva sus salidas como evidencia. Los notebooks principales de `notebooks/` resumen este
trabajo siguiendo la estructura de la entrega.

| Notebook | Etapa CRISP-DM | Contenido | Resultado guardado |
|---|---|---|---|
| `01_adquisicion_eda` | Comprensión de los datos | Descarga de Kaggle (Champa et al.), PhiUSIIL y SpamAssassin con hash SHA-256 por archivo | `data/manifiestos/g17-phishing-raw-v1.json` |
| `01b_adquisicion_complementaria` | Comprensión de los datos | Nazario anual, phishing_pot (commit fijado) y PhishTank | `data/manifiestos/g17-phishing-complemento-v1.json` |
| `01c_validacion_ioc_utils` | Preparación | Defanging aplicado a todo el corpus: 0 IOC vivos | — |
| `02_eda_dqr` | Comprensión de los datos | EDA y reporte de calidad de datos (preguntas Q1 a Q7) | — |
| `03_preparacion_splits` | Preparación | Diccionario de etiquetas, deduplicación, particiones por fuente y pliegues fuera de distribución | — |
| `04_rama_url` | Modelado | XGBoost sobre variables léxicas de URL; control del artefacto de PhiUSIIL; dominios disjuntos | `results/metrics/rama_url_v1.json` |
| `05_baseline` | Modelado | TF-IDF + regresión logística; búsqueda de C | `results/metrics/baseline_v1.json` |
| `06_distilbert` | Modelado | Ajuste fino de DistilBERT (partición principal y pliegues fuera de distribución) | `results/metrics/distilbert_v1_*.json` |
| `07_fusion` | Modelado | Fusión tardía (variantes V0 a V3), calibración y umbral por FPR | `results/metrics/fusion_v1.json` |
| `08_validacion_inferencia` | Evaluación | Inferencia de extremo a extremo y contrato JSON | `results/metrics/inferencia_v1.json` |
| `09_publicar_hf` | Despliegue | Publicación de artefactos en Hugging Face Hub y prueba de la API | `results/metrics/despliegue_v1.json` |
| `10_datos_es` | Comprensión de los datos | SpaPhish y SpearPhishMX: validación y armonización | `results/metrics/datos_es_v1.json` |
| `10b_spam_es_traduccion` | Preparación | Espejo traducido inglés a español (OPUS-MT) con IOC protegidos | `results/metrics/spam_es_v1.json` |
| `11_distilbert_multilingue` | Modelado | DistilBERT multilingüe: experimentos E0, E1, E2 y pliegues por fuente española | `results/metrics/multilingue_*.json` |
| `12_fusion_es` | Modelado | Fusión de la ruta española; exclusión de la rama URL (decisión D21) | `results/metrics/fusion_es_v1.json` |
| `13_validacion_bilingue` | Evaluación | Validación de la ruta bilingüe y publicación de la versión v2 | `results/metrics/bilingue_v1.json` |
| `14_muestra_kpi` | Evaluación | Muestra de 200 correos de prueba para los KPI de integración y triaje | — |
| `15_fpr_correo_corporativo` | Evaluación | Falsos positivos en correo corporativo (Enron) y umbral operativo (decisión D27) | `results/metrics/fpr_enron_v1.json` |
| `16_diagnostico_sobreajuste` | Evaluación | Diagnóstico de sobreajuste y subajuste (Semana 3) | `results/metrics/semana3/` |

## Notas sobre la versión publicada

* Se conservó la última versión ejecutada de cada notebook. Para elegirla se comparó el código con
  la versión final del proyecto y el resumen impreso con el archivo de `results/metrics` que el
  mismo notebook escribió. Las versiones intermedias se descartaron.
* `05_baseline`: ninguna de las copias ejecutadas disponibles corresponde a la corrida que produjo
  el modelo publicado; la que se conserva difiere en el cuarto decimal (por ejemplo, F1 de
  validación con C = 8 de 0,9874 frente a 0,9873). Los valores de referencia son los de
  `results/metrics/baseline_v1.json`, escrito por la corrida que generó el artefacto publicado.
  `notebooks/03_modelado` reentrena la línea base con `src/train.py`: obtiene el mismo C, el mismo
  F1 de validación (0,9873) y el 100 % de las predicciones iguales a las del modelo publicado. La
  variación de 0,0001 entre ejecuciones es numérica.
* `09_publicar_hf`: se retiró de la salida la clave de la API que la celda imprimía al generarla.
  Una clave nunca debe quedar en un archivo versionado.
* Se normalizó el formato de los comentarios de encabezado de las celdas y la etiqueta del bloque
  de resumen final. El código ejecutable y los valores impresos no se modificaron.
* Los notebooks importan los módulos con los nombres que tenían durante la experimentación:
  `data_prep` (hoy `src/data_processing.py`) e `inference` (hoy `src/model.py`). Para
  reejecutarlos sin cambios se usan los mismos módulos copiados en la carpeta `src` de Drive.
