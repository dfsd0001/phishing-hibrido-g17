# Modelos

Los artefactos entrenados no están en GitHub. Se publican en un repositorio **privado** de Hugging
Face Hub, versionados con etiquetas inmutables:

| Repositorio | Etiqueta vigente | Etiqueta anterior |
|---|---|---|
| `dennysSalazar/g17-phishing-hibrido` | `v2`: ruta inglesa V3 y ruta española V1_es (15 archivos) | `v1`: solo ruta inglesa (9 archivos) |

**Por qué no están en el repositorio.**

1. **Tamaño.** El DistilBERT inglés pesa cerca de 268 MB y el multilingüe es mayor, por encima del
   límite de 100 MB por archivo de GitHub.
2. **Licencias de los datos.** Los modelos se entrenaron con corpus de terceros, uno de ellos con
   licencia no comercial (phishing_pot, CC BY-NC 4.0).
3. **Uso dual.** Con los pesos, un atacante podría probar sus correos sin límite hasta evadir el
   detector. Mantenerlos privados reduce ese riesgo (ver `docs/consideraciones_eticas.md`, sección 7).

**Acceso para evaluación.** La demostración pública (`nube/README.md`) ya usa el modelo, así que
para probarlo no hace falta ningún token. Para reproducir el despliegue local, el equipo entrega por un
canal privado un token de Hugging Face *Fine-grained* de **solo lectura**, limitado a este repositorio
y revocable. El token nunca se escribe en el código ni en este repositorio. Cada persona y cada
despliegue (local o en la nube) recibe su propio token, con un nombre que identifica a quién pertenece,
para poder revocarlo sin afectar a los demás; al terminar la evaluación del proyecto se revocan todos.

## Descarga

La API descarga los artefactos sola al arrancar (variables `HF_TOKEN`, `MODEL_REPO` y
`MODEL_REVISION` de `deploy/.env`). Para usarlos en los notebooks o fuera de Docker:

```bash
export HF_TOKEN=<token de solo lectura>
python -c "
from huggingface_hub import snapshot_download
snapshot_download('dennysSalazar/g17-phishing-hibrido', revision='v2', local_dir='.',
                  allow_patterns='models/*')
"
```

Desde la raíz del repositorio, el comando deja los archivos en `models/`, que es donde los busca `src/model.py`
(`Detector.desde_directorio`). La carpeta está excluida de Git salvo este README y `manifiesto.json`.

## Artefactos de la versión v2

| Archivo | Componente | Formato |
|---|---|---|
| `models/distilbert_v1/` (`config.json`, `model.safetensors`, `tokenizer.json`, `tokenizer_config.json`) | DistilBERT de la ruta inglesa | Transformers |
| `models/baseline_tfidf_lr_v1.joblib` | Línea base TF-IDF y regresión logística | joblib (scikit-learn 1.6.1) |
| `models/url_xgb_v1b_correos.json` | Rama URL | XGBoost 3.4.1 |
| `models/url_xgb_v1.meta.json` | Variables y categorías de TLD de la rama URL | JSON |
| `models/fusion_v1.joblib` | Meta-clasificador V3 calibrado y umbral de validación | joblib |
| `models/fusion_v1.meta.json` | Metadatos de la fusión inglesa | JSON |
| `models/distilbert_multi_v1/` (4 archivos) | DistilBERT multilingüe de la ruta española | Transformers |
| `models/fusion_es_v1.joblib` | Meta-clasificador V1_es calibrado | joblib |
| `models/fusion_es_v1.meta.json` | Metadatos de la fusión española | JSON |

El equivalente al "mejor modelo" de un proyecto con un solo estimador es el conjunto formado por las
tres ramas y `fusion_v1.joblib`, que las combina. Los archivos `.joblib` solo deben cargarse desde este
repositorio de confianza: deserializar un archivo joblib ejecuta código.

## Ficha del modelo

| Campo | Descripción |
|---|---|
| **Nombre y versión** | Detector híbrido de phishing, `fusion_v1`, variante V3 (inglés) y V1_es (español), artefactos `v2` |
| **Autores** | Grupo 17: Dennys Francisco Salazar Domínguez y Lenin Bolívar González Rivadeneira, Maestría en Inteligencia Artificial, UEES, octubre de 2026 |
| **Tipo** | Clasificación de correos en tres clases por fusión tardía de DistilBERT, TF-IDF con regresión logística y XGBoost sobre URL, con meta-clasificador calibrado |
| **Uso previsto** | Apoyo al triaje de correos reportados en un SOC, con decisión final de un analista |
| **Usuarios previstos** | Analistas de seguridad y usuarios que reportan correos sospechosos |
| **Fuera de alcance** | Bloqueo o borrado automático, escaneo masivo de buzones, evaluación de empleados, idiomas distintos del inglés y el español, adjuntos e imágenes |
| **Datos de entrenamiento** | 54.684 correos en inglés (CEAS 2008, SpamAssassin, Nigerian Fraud, Nazario, phishing_pot); para el español, SpaPhish, SpearPhishMX y un espejo traducido. Ver `data/README.md` |
| **Datos de evaluación** | Partición de prueba de 8.203 correos, pliegues con un corpus completo fuera del entrenamiento, 2.000 correos de Enron y 641 correos nativos en español |
| **Umbral** | 0,8586 en la ruta inglesa (decisión D27); 0,8469 en la ruta española |

**Métricas (umbral operativo)**

| Métrica | Valor | IC 95 % |
|---|---:|---|
| F1 macro, prueba en inglés | 0,9869 | 0,9841 a 0,9895 |
| Recall de phishing, prueba en inglés | 96,4 % | 95,4 a 97,3 |
| Precisión de phishing, prueba en inglés | 99,1 % | 98,6 a 99,5 |
| FPR de phishing, prueba en inglés | 0,19 % | 0,10 a 0,31 |
| FPR en correo corporativo (Enron) | 1,3 % | 0,8 a 2,2 |
| Recall de phishing con phishing_pot fuera del entrenamiento | 83,5 % | |
| Recall de phishing, español nativo | 93,5 % | 90,6 a 95,6 |
| FPR, español nativo | 3,5 % | 1,9 a 6,6 |
| Latencia de punta a punta, percentil 95 | 275 ms | |

**Factores que cambian el desempeño:** longitud del texto (recall de 93,2 % por debajo de 300
caracteres), ausencia de URL (94,4 %), corpus o tipo de campaña nunca vistos, idioma y phishing
dirigido.

**Consideraciones éticas y advertencias:** ver `docs/consideraciones_eticas.md`. El riesgo es la
probabilidad de phishing; un correo puede salir como spam con riesgo alto si no alcanza el umbral.
