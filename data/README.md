# Datos

Los correos de entrenamiento y evaluación provienen de corpus públicos de terceros. **El repositorio
no los redistribuye**: contienen correos reales con datos personales y algunas licencias no lo
permiten (phishing_pot es CC BY-NC 4.0). Aquí se versionan solo los manifiestos con las huellas SHA-256
de cada archivo descargado, para que cualquiera pueda obtener exactamente los mismos datos y
comprobarlo.

## Estructura

```
data/
├── manifiestos/
│   ├── g17-phishing-raw-v1.json          Kaggle, PhiUSIIL y SpamAssassin (18 archivos)
│   └── g17-phishing-complemento-v1.json  Nazario anual, phishing_pot y PhishTank (15 archivos)
├── raw/          Archivos originales, inmutables (no versionado)
└── processed/    Tablas derivadas en Parquet (no versionado)
```

Las tablas que leen los notebooks se generan en este orden (todas guardan el texto ya defangeado):

| Tabla | Contenido | Generada por |
|---|---|---|
| `interim/emails_v0.parquet` | 94.566 correos de todas las fuentes, antes de exclusiones | `notebooks/experimentos/02_eda_dqr` |
| `eda/dqr_v1.json` | Reporte de calidad de datos | `notebooks/experimentos/02_eda_dqr` |
| `processed/emails_v1.parquet` | Dataset final en inglés: 54.684 correos con particiones y pliegues | `notebooks/experimentos/03_preparacion_splits`, reproducido por `notebooks/02_preprocesamiento` |
| `processed/url_scores_v1.parquet` | Puntajes de la rama URL por correo | `notebooks/experimentos/04_rama_url` |
| `processed/text_scores_distilbert_v1.parquet` | Probabilidades de DistilBERT | `notebooks/experimentos/06_distilbert` |
| `processed/emails_es_v2.parquet` | Español nativo y espejo traducido | `notebooks/experimentos/10_datos_es` y `10b_spam_es_traduccion` |
| `processed/text_scores_multi_es_v1.parquet` | Probabilidades del DistilBERT multilingüe | `notebooks/experimentos/11_distilbert_multilingue` |

## Fuentes

### Entrenamiento y evaluación en inglés

| Fuente | Versión o commit | Licencia | Uso |
|---|---|---|---|
| Phishing Email Dataset, Kaggle (`naserabdullahalam/phishing-email-dataset`) | Versión 1, descargada el 28/09/2026 | La ficha de Kaggle no declara licencia. Los archivos por corpus tienen los mismos nombres que el conjunto curado de A. I. Champa publicado en Zenodo con licencia CC BY 4.0 | CEAS_08, SpamAssasin y Nigerian_Fraud; Enron, Ling y Nazario se excluyen (ver `docs/analisis_datos.md`) |
| Nazario Phishing Corpus, archivos anuales 2015 a 2025 (https://monkey.org/~jose/phishing/) | Descarga del 28/09/2026 | CC BY 4.0, según el README del autor | Phishing |
| phishing_pot (https://github.com/rf-peixoto/phishing_pot) | Commit `49f63777126b0bdb9eb1f6e770a5c3f9df2b0306` | CC BY-NC 4.0 | Phishing, solo correos en inglés |

### Ruta en español

| Fuente | Versión | Licencia | Uso |
|---|---|---|---|
| SpaPhish: A Spanish Dataset for Phishing and Psychological Pattern Detection, Mendeley Data (doi:10.17632/hz2d6gz7pc.5) | Versión 5 | CC BY 4.0 | Phishing y legítimo nativos (1.343 correos tras la limpieza) |
| Spear-Phishing en español: dataset de correos dirigidos con señales de personalización (SpearPhishMX), Mendeley Data (doi:10.17632/h4bxjk84jb.2) | Versión 2, publicada el 15/02/2026 | CC BY 4.0. Los autores lo publican para investigación defensiva, con datos personales anonimizados y URL defangeadas | Phishing dirigido y legítimo nativos (2.925 correos tras la limpieza) |
| Espejo traducido del corpus inglés | Traducción con `Helsinki-NLP/opus-mt-en-es` (modelo CC BY 4.0) | La de los corpus de origen | Solo entrenamiento de la ruta española |

### Validación externa y evidencia auxiliar

| Fuente | Licencia | Uso |
|---|---|---|
| Enron-Spam (Metsis, Androutsopoulos y Paliouras, 2006), copia `SetFit/enron_spam` en Hugging Face | Ver la ficha de la copia | 2.000 correos legítimos para medir falsos positivos en correo corporativo |
| PhiUSIIL Phishing URL Dataset, UCI Machine Learning Repository, id 967 | CC BY 4.0 | Evidencia del artefacto de ruta que descartó esta fuente para la rama URL |
| Copia de PhishTank (https://github.com/arvindeybram/phishing), commit `619b0e2066838dc5780032028292ccfd5255b075` | Términos de PhishTank | Validación externa de la rama URL |
| SpamAssassin Public Corpus (https://spamassassin.apache.org/old/publiccorpus/) | Ver el readme del directorio | Descargado como respaldo; no se usó |
| Cuatro correos de phishing publicados por malware-traffic-analysis.net (05/05/2020) | No publicada | Validación cualitativa de la interfaz; se identifican por su huella en `results/metrics/validacion_externa_mta.json` y no se copian |

## Cómo obtener los datos

1. Ejecutar `notebooks/experimentos/01_adquisicion_eda` (Kaggle, PhiUSIIL y SpamAssassin) y
   `01b_adquisicion_complementaria` (Nazario anual, phishing_pot y PhishTank). Ambos descargan en
   `data/raw/`, calculan el SHA-256 de cada archivo y lo comparan con el manifiesto. Una discrepancia
   detiene la ejecución.
2. Para el español, descargar SpaPhish v5 y SpearPhishMX v2 desde Mendeley Data con el navegador
   (*Download All*), descomprimirlos en `data/raw/es/spaphish/` y `data/raw/es/spearphishmx/` y
   ejecutar `10_datos_es` y `10b_spam_es_traduccion`.
3. Ejecutar los notebooks de la tabla de la sección *Estructura* para generar las tablas derivadas.

Para comprobar un archivo a mano:

```bash
sha256sum data/raw/kaggle_phishing_email/CEAS_08.csv
# 22375e7d5f5a8229dbe987914ee9b3705656c590038662a7df6054629b376074
```

## Reglas de manejo

* El crudo es inmutable: solo lo lee código y nunca se abre en un cliente de correo ni en un navegador.
* Toda tabla derivada guarda las URL e IPv4 defangeadas (`hxxps[://]dominio[.]com`). El refang ocurre
  solo en memoria, para calcular variables, y ninguna URL se resuelve ni se visita.
* `data/raw/` y `data/processed/` están excluidos de Git (`.gitignore`).

## Referencias

* Champa, A. I. (2023). *Phishing Email Curated Datasets* [conjunto de datos]. Zenodo.
  https://doi.org/10.5281/zenodo.8339691
* Diaz, J. M., Martínez Cruz, A. y Bustio Martinez, L. (2026). *Spear-Phishing en español: dataset de
  correos dirigidos con señales de personalización (SpearPhishMX)* (versión 2) [conjunto de datos].
  Mendeley Data. https://doi.org/10.17632/h4bxjk84jb.2
* Bustio-Martínez, L., Fuentes-Fuentes, V. I., Agudelo Fuentes, L. F., Herrera-Semenets, V.,
  Llanes-Guilarte, D., Trujillo-Fernández, F. A., Cardeña-Matamoros, A. C., Betancourt-Moreno, C. F.,
  Molano-Jiménez, A. G. y van den Berg, J. (2026). Spanish phishing and legitimate email dataset with
  technical and psychological annotations. *Data in Brief, 67*, 112890.
  https://doi.org/10.1016/j.dib.2026.112890
* Prasad, A. y Chandra, S. (2024). PhiUSIIL: A diverse security profile empowered phishing URL
  detection framework based on similarity index and incremental learning. *Computers & Security*.
  https://doi.org/10.1016/j.cose.2023.103545
