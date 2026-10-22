# Bitácora de decisiones y evidencia — Proyecto Integrador MIAR0545 · Grupo 17

**Proyecto:** Sistema Inteligente de Detección y Clasificación de Phishing Híbrido (NLP + Análisis de URLs)
**Equipo:** Dennys Francisco Salazar Domínguez · Lenin Bolívar González Rivadeneira
**Versión:** v4, proyecto cerrado (20/10/2026). Las versiones anteriores se cerraron con la fase de modelado (03/10) y con la integración (14/10).
**Regla de este documento:** cada afirmación tiene su evidencia (prueba, log o resumen de notebook). Lo no medido se marca como *estimación*. Todo IOC aparece defangeado.

**Nota sobre los nombres.** Las secciones 1 a 7 conservan los nombres de su momento: `data_prep.py` es hoy `src/data_processing.py`, `inference.py` es `src/model.py`, y los notebooks numerados de 01 a 16 están en `notebooks/experimentos/`. Los cinco notebooks de `notebooks/` resumen ese trabajo y lo reproducen desde el código del repositorio.

---

## 1. Estado general

| Sprint | Alcance | Estado | Evidencia |
|---|---|---|---|
| S1 (14–20/09) | Definición, SMART, estado del arte | Cerrado | 8 entregables de Semana 1 |
| S2 (21/09–04/10) | Datos, EDA, preparación, rama URL, baseline | **Cerrado el 02/10** | Notebooks 01–05 ejecutados en Colab |
| S3 (05–18/10) | DistilBERT, fusión, calibración, evaluación cruzada | **Cerrado técnicamente el 03/10** (adelantado) | Notebooks 06 v1.1 y 07 ejecutados en Colab |
| S4 (19–25/10) | Integración (n8n, DFIR-IRIS, Wazuh), interfaz, documentación | **Cerrado el 20/10** (integración adelantada al 14/10) | Lote KPI, triaje cronometrado, notebooks 01–05 ejecutados con datos reales, interfaz probada con el modelo real |

**Desvío registrado:** el EDA (hito S2 del Canvas, 27/09) se entregó junto con el baseline dentro del Sprint 2. No se movió ninguna meta.

---

## 2. Artefactos producidos

### Código (`src/`) — 355 pruebas en verde (Colab y entorno local)

| Módulo | Versión | Función |
|---|---|---|
| `ioc_utils.py` | v1.2 | Extracción de URLs/IPv4, defang/refang, verificador de IOCs vivos |
| `data_prep.py` | v0.5 | Parser de correos (.eml/mbox), `texto_plano`, hash, año, `texto_para_modelo` |
| `url_features.py` | v1.0 | 22 features léxicas desde la cadena; excluye esquema y www |

### Notebooks

| Notebook | Propósito | Salidas principales |
|---|---|---|
| `01_adquisicion_eda` | Descarga y congelamiento del snapshot v1 | `manifest_g17-phishing-raw-v1.json` (18 archivos, SHA-256) |
| `01b_adquisicion_complementaria` | Nazario anual, phishing_pot, PhishTank | `manifest_g17-phishing-complemento-v1.json` (15 archivos, commits fijados) |
| `01c_validacion_ioc_utils` | KPI de defanging sobre corpus real | 0 IOCs vivos en 94.566 textos |
| `02_eda_dqr` | EDA y Data Quality Report (Q1–Q7) | `emails_v0.parquet`, `dqr_v1.json`, `revision_manual_pot.csv` |
| `03_preparacion_splits` | Diccionario de etiquetas v1, deduplicación, splits, folds | `emails_v1.parquet`, `diccionario_etiquetas_v1.json` |
| `04_rama_url` | Rama URL (PhiUSIIL vs URLs de correos) | `url_xgb_v1.json`, `url_xgb_v1b_correos.json`, `url_scores_v1.parquet` |
| `05_baseline` | TF-IDF + Regresión Logística | `baseline_tfidf_lr_v1.joblib`, `baseline_v1.json` |
| `06_distilbert` v1.1 | Fine-tuning de DistilBERT (GPU T4): principal + 4 folds, reanudable | `models/distilbert_v1/`, `text_scores_distilbert_v1*.parquet`, `distilbert_v1_*.json` |
| `07_fusion` | Meta-clasificador (blending en validación), calibración, riesgo 0–100, fusión fuera de distribución | `fusion_v1.joblib`, `fusion_v1.meta.json`, `fusion_v1.json` |

**Nota de numeración:** el plan original del repositorio era 01 adquisición+EDA, 02 preparación, 03 baseline, 04 modelos, 05 fusión. La numeración real es la de la tabla.

---

## 3. Datos: formato de entrega, lectura y validación

| Fuente | Formato del proveedor | Lectura | Validación realizada | Uso |
|---|---|---|---|---|
| Kaggle Phishing Email Dataset (v1) | 7 CSV, texto ya extraído | pandas (utf-8 → latin-1) | Suma de subcorpus = consolidado (82.486); semántica de etiqueta por archivo; nulos; duplicados; idioma; URLs; fechas | CEAS_08, SpamAssasin y Nigerian_Fraud entran; el resto se excluye (D2, D3) |
| Nazario anual 2015–2025 | 11 mbox crudos (RFC 5322/MIME) | `mailbox` + `data_prep.texto_de_email` | 3.466 correos; 2015–2021 = 1.916, igual a la cifra publicada; 0 errores de parseo; 92,1 % con URL | Clase phishing (origen 2) |
| phishing_pot (commit 49f6377) | ZIP con 8.614 .eml crudos | Mismo parser | 0 errores de parseo; 51 % inglés; 20,5 % duplicados; fuga `phishing@pot` detectada y corregida | Clase phishing (origen 3), solo inglés |
| PhiUSIIL (UCI id 967) | CSV de 56 columnas vía `ucimlrepo` | pandas | 235.795 filas y 134.850/100.945 exactos; fugas de etiqueta encontradas (Q7) | Solo evidencia del artefacto (D6) |
| PhishTank (GitHub, commit 619b0e2) | CSV de URLs, solo positivos, 2008–2018 | pandas | 32.239 URLs | Validación externa (M3) |
| SpamAssassin crudo | Tarballs .tar.bz2 | — | Descargado y con hash | Reserva; no se usa (el CSV de Kaggle lo cubre) |

**Integridad:** todo el crudo está congelado con SHA-256 y se re-verificó (0 discrepancias). **Política de almacenamiento:** el crudo es inmutable, solo lo lee código y nunca se abre en un cliente de correo ni en un navegador. Todo artefacto derivado se guarda defangeado.

---

## 4. Decisiones (con evidencia)

| # | Decisión | Evidencia |
|---|---|---|
| D1 | Nigerian_Fraud se mantiene en phishing; métricas con y sin él | Decisión del equipo; sin él, phishing queda con 2 orígenes |
| D2 | Excluir el `Nazario.csv` de Kaggle; usar Nazario anual crudo | Q5: mismos años (2015–2022); 439 hashes idénticos; Q4: el CSV perdió los enlaces (16,2 % con URL vs 92,1 % en el crudo) |
| D3 | Excluir Enron y Ling | Q4: contienen "http" (18,8 % y 38,8 %) pero 0 % de URLs válidas (texto tokenizado); sin fecha. Tras excluirlas, el % sin URL quedó parejo entre clases (27–33 %) |
| D4 | Filtro de idioma (inglés) en phishing_pot y Nazario anual | Q3: phishing_pot 51 % inglés; el resto de fuentes ≥ 94 % |
| D5 | `texto_para_modelo`: sin HTML; URL/IP/email/año/dominio propio → marcadores | Evita que el texto aprenda dominios, fechas o el buzón de cada corpus (Q5 y sonda de fuga) |
| D6 | Rama URL = variante B (URLs de correos con etiqueta heredada); PhiUSIIL solo como evidencia | M1: esquema+www AUC 0,988; 100 % de URLs legítimas sin ruta. M4: AUC 0,67 en correos y FPR legítimo 96 %. M6: AUC 0,88 con dominios disjuntos |
| D7 | Fusión entrenada sobre el split de validación (blending) | Generar predicciones fuera de fold de DistilBERT no cabe en el plazo |
| D8 | Criterio adicional del S3: DistilBERT y fusión deben mejorar el recall fuera de distribución | El baseline ya cumple las metas dentro de la distribución (sección 5) |
| D9 | Política de umbral: el más bajo con FPR ≤ 1 % en validación (máximo recall), en lugar de "recall 95 % en validación" | DistilBERT satura sus probabilidades (umbral 0,9946; loss final 0,0003): fijar un recall exacto era inestable y dejaba fuera al phishing de fuentes nuevas |
| D10 | Modelo final = V3: meta-clasificador sobre DistilBERT + baseline + rama URL, calibración isotónica, riesgo = round(100·P(phishing)) | Mejor o empatada en los 4 folds fuera de distribución (promedio 93,4 % vs 86–87 % del resto). Coherente con el diagrama de la Ficha, cuya rama de texto ya incluía DistilBERT y TF-IDF |
| D11 | En producción v1 se mantiene la rama URL entrenada con dominios disjuntos | El meta-clasificador aprendió sobre esos puntajes; reentrenarla con todos los dominios inflaría su peso sin poder recalibrar |
| D12 | La API corre como contenedor en el docker-compose local (red del SOC); el modelo sigue versionado en HF Hub (privado, tag `v1`) | HF respondió 402 al crear el Space: los Spaces Docker y Gradio en CPU gratuita ahora requieren PRO (03/10/2026). Ventajas: USD 0, los correos no salen de la red y no hay arranque en frío. Desalinea la Ficha (capa 3 en HF Spaces) |
| D13 | Puerta de idioma (contrato v1.1): `idioma_detectado` + advertencia `idioma_no_soportado`; n8n lo envía a revisión manual | Prueba del 09 desde el Hub: un correo legítimo en español se clasificó como phishing (modelo entrenado solo en inglés) |
| D14 | Versiones fijadas del stack: n8n 2.41.6 · DFIR-IRIS v2.4.29 (compose oficial) · Wazuh manager 4.14.8 (sin indexer ni dashboard, por RAM) · ingesta en Wazuh vía `POST /events` | Últimas versiones publicadas al 03/10/2026; `POST /events` verificado en la especificación de la API de Wazuh 4.14.8 |
| D15 | Soporte de español por vía B (DistilBERT multilingüe). Datos: SpaPhish + SpearPhishMX (nativos, phishing/legítimo) + spam en español por traducción automática (OPUS-MT en-es, CC BY 4.0) de CEAS/SpamAssassin | No hay spam público en español; traducir un corpus "gold" es técnica estándar ante escasez de recursos. Vía 3 (spam sintético LLM) queda declarada y desactivada; vías 1 (pedir SPEMC) y 4 (filtrar multilingüe) como respaldo |
| D16 | `ioc_utils` v1.3: separa esquemas pegados a texto previo (`...com.mxhttps://x`); reactivar la verificación de IOCs vivos (NO comentarla: es el KPI de defanging) | 13 registros de SpaPhish evadían el defang por esquema concatenado sin separador; la verificación del 10 los detectó correctamente |
| D17 | Espejo traducido completo (3 clases): el AUC traducido-vs-nativo sigue ~0,997, pero ya NO está correlacionado con la clase (spam, phishing y legítimo comparten el estilo de traducción). El artefacto deja de ser un problema de etiqueta | Antes solo el spam estaba traducido (artefacto = clase). Con las 3 clases traducidas por igual, "suena a traducción" no predice la clase |
| D18 | Regla de evaluación cross-lingual: el español NATIVO (SpaPhish/SpearPhishMX) solo se usa para EVALUAR; el traducido solo para ENTRENAR. E0 = solo inglés; E1 = inglés + español traducido. Verificado: 0 fuga de nativo a train/val | Es la única forma de medir honestamente la transferencia al español real. Sin spam nativo, el test en español mide sobre todo phishing vs legítimo (declarado) |
| D19 | Resultado E0/E1: el fallo en español NO es de idioma sino de TIPO de phishing. SpaPhish (masivo) transfiere bien (AUC 0,85 en E1); SpearPhishMX (dirigido) cae al azar (AUC 0,49). E1 no causa retroceso en inglés (F1 0,983→0,991). Se agrega E2 (con español nativo de train) y E2-LOSO entre fuentes en español | El inglés de entrenamiento es phishing masivo; el phishing dirigido imita correo corporativo legítimo y evade el detector. Hallazgo coherente con la literatura |
| D20 | Modelo de texto en español = E2 (`distilbert_multi_v1`). Test nativo held-out: AUC 0,984 · recall phishing 93,5 % · recall legítimo 96,1 % · F1 de las 2 clases presentes 0,944. Sin retroceso en inglés (F1 0,989). LOSO: SpaPhish fuera AUC 0,615; **SpearPhishMX fuera AUC 0,408 (recall 7,6 %)** | El F1 macro de 3 clases (0,63) es engañoso: promedia spam con soporte 0 en español nativo. Las filas "por fuente" de E2 no son válidas (incluyen su split de train). Frontera real: el phishing dirigido de un estilo no visto no se detecta |
| D21 | Ruta española = V1_es (DistilBERT multilingüe E2 + meta binario calibrado), SIN rama URL. Regla: si la rama URL sola no supera el azar en ninguna fuente nativa, se excluye | Rama URL en español: AUC 0,374 (SpaPhish) y 0,445 (SpearPhishMX), invertida: patrón aprendido con URLs de correo en inglés que no transfiere. NO es efecto de la traducción: los IOCs se protegen antes de traducir y la rama URL solo se evaluó con correos nativos. V2_es ganó en val por 1 correo; en test V1_es es igual o mejor |
| D22 | Alcance final del español (documentado): test nativo held-out con V1_es: recall phishing 93,5 %, **FPR 3,5 % (IC 95 % 1,9–6,6)**, AUC 0,984. FPR por encima de la meta de 2 %: los 9 falsos positivos vienen del legítimo de SpaPhish (9/95). Phishing dirigido de estilo no visto no se detecta (LOSO SpearPhishMX: recall 7,6 %). API v1.2 enruta en→V3, es→V1_es, otros idiomas→advertencia; artefactos en el Hub con tag v2 | Cierre de la vía B: se limita el alcance y se documenta la realidad en lugar de seguir iterando |

---

## 5. Resultados medidos

### Corpus final (`emails_v1.parquet`)
54.684 correos: legítimo 21.379 (CEAS, SpamAssassin) · spam 23.386 (CEAS, SpamAssassin) · phishing 9.919 = 18,1 % (Nigerian 3.290, Nazario anual 2.927, phishing_pot 3.702). Split 70/15/15 estratificado por clase × fuente; 0 hashes compartidos entre splits.

### Baseline TF-IDF + RL (hito S3), con `data_prep` v0.5

| Métrica (test, misma distribución) | Resultado | Meta SMART |
|---|---|---|
| F1 macro | 98,70 % | ≥ 90 % |
| Recall phishing (umbral fijado en validación) | 96,17 % | ≥ 95 % |
| FPR phishing | 0,27 % | ≤ 2 % |
| Legítimo marcado como phishing | 0,03 % (1 de 3.207) | — |
| Recall phishing sin Nigerian | 95,18 % | ≥ 95 % |

Los baselines de la Matriz de KPIs (F1 75 %, Recall 80 %) eran estimaciones; quedan reemplazados por estas cifras medidas.

### Evaluación fuera de distribución (la cifra honesta)

| Fuente no vista en el entrenamiento | Recall phishing del texto | AUC de la rama URL (variante B) |
|---|---|---|
| phishing_pot | 26,5 % | 0,947 |
| Nigerian_Fraud | 26,8 % | 0,527 |
| Nazario anual | 84,3 % | 0,889 |
| Phishing 2025+ (temporal) | 65,9 % | — |

Fuente legítimo/spam fuera: CEAS → recall spam 44,2 %; SpamAssassin → recall spam 28,3 %.

**Lectura:** las dos ramas fallan en fuentes distintas (phishing_pot: el texto falla y la URL acierta). Es la evidencia empírica a favor de la arquitectura híbrida. Nigerian_Fraud no generaliza en ninguna de las dos.

### Rama URL
M2 PhiUSIIL interno: AUC 0,93 · M3 PhishTank: 98,9 % de detección (inflado por el artefacto de ruta) · M5 latencia: 6–8 ms por URL.

### DistilBERT (06, GPU T4; 3 épocas, ~15 min por entrenamiento)
Test en la misma distribución, predicción directa: F1 98,99 % · recall phishing 98,72 % · FPR 0,46 %. Latencia en CPU: **208 ms por correo** (KPI < 1 s; volver a medir en HF Spaces).
Con la política anterior (recall 95 % en validación), fuera de distribución frente al baseline: phishing_pot 44,3 % vs 26,5 % · temporal 2025+ 82,9 % vs 65,9 % · Nigerian 12,1–16,4 % vs 26,8 % · Nazario 78,2 % vs 84,3 %. No es mejor en todo.

### Fusión (07) — misma política para todas las variantes (umbral con FPR ≤ 1 % en validación)

**Test en la misma distribución (modelo elegido V3):** F1 98,74 % · **recall phishing 99,66 %** · **FPR phishing 0,91 %** (legítimo→phishing 0,22 %; el resto es spam→phishing) · Brier 0,011 · ECE 0,0055. Riesgo: mediana 0 en legítimo y spam, 100 en phishing; 94,3 % del phishing con riesgo ≥ 90; 0 % del legítimo con riesgo ≥ 50.

| Phishing no visto (recall, FPR ≈ 1 %) | V0 baseline | V1 DistilBERT | V2 DistilBERT+URL | **V3 todo** |
|---|---|---|---|---|
| phishing_pot | 68,5 % | 73,6 % | 83,5 % | **83,5 %** |
| Nigerian_Fraud | 91,7 % | 84,8 % | 67,8 % | **94,1 %** |
| Nazario anual | 95,5 % | 96,3 % | 96,3 % | **97,4 %** |
| Temporal 2025+ | 93,3 % | 94,1 % | 97,9 % | **98,6 %** |
| **Promedio** | 87,3 % | 87,2 % | 86,4 % | **93,4 %** |

**Lectura honesta:**
1. La mayor parte del salto respecto al Sprint 2 (50,9 % → 87 %) viene de D9, no de los modelos. La comparación válida es entre columnas.
2. Con la misma política, DistilBERT solo (87,2 %) ≈ baseline solo (87,3 %). Su valor aparece al combinarlo.
3. La rama URL aporta +10 puntos en phishing_pot, pero perjudica en Nigerian_Fraud (V2 67,8 %); el baseline lo compensa en V3.
4. Las cifras en la misma distribución son optimistas, porque el meta-clasificador se ajusta en validación, que comparte distribución con test. Las cifras honestas son las de esta tabla.

---

### Inferencia empaquetada (08, Colab CPU)
`src/inference.py` desde el correo frente al notebook 07, sobre 322 correos de test: texto de entrada idéntico 100 % · misma clase 100 % (ΔP(phishing) mediana 0, p95 0) · n_urls idéntico 97,2 % · contrato válido 322/322 · 0 IOCs vivos · **latencia media 200 ms, p95 348 ms** · carga inicial 31 s · acierto 99,7 %.

### Revisión manual de phishing_pot (50 correos)
phishing 42 % · estafa 22 % · spam 34 % · legítimo 2 %. Bien etiquetados según D1: **64 % (IC 95 %: 50,1–75,9)**. Proyección: entre 892 y 1.847 de los 3.702 correos de esta fuente tienen una etiqueta incorrecta. Se declara como limitación; la limpieza asistida queda como trabajo futuro.

## 6. Errores encontrados y corregidos

| Componente | Error | Cómo se detectó | Corrección |
|---|---|---|---|
| `ioc_utils` v1.0 | 6 textos con IOC vivo (esquema duplicado `hxxp[://]http...`, enlaces Markdown) | KPI sobre corpus real (99,993 %) | v1.2 + regresiones |
| `ioc_utils` v1.1 | `www...` contado como URL; IP al final de oración no detectada | Pruebas dirigidas | v1.1 |
| `ioc_utils` v1.1 | Regresión: una URL real tras un comodín quedaba viva y oculta al verificador | Prueba sobre 8.614 correos de phishing_pot | v1.2 |
| `url_features` | La `@` en la autoridad (`marca@host-real`) desaparecía | Pruebas | v1.0 |
| `data_prep` v0.3 | **Fuga de etiqueta:** `phishing@pot` sin enmascarar (2.782 correos) | Términos de mayor peso del baseline | v0.4 |
| `data_prep` v0.4 | "monkey" (buzón de Nazario) en el 23 % de Nazario anual | Sonda de fuga del notebook 03 | v0.5: `__dominio_propio__` |
| Rama URL variante B | AUC 0,98 inflado por memoria de dominios (89,9 % de hosts de test vistos en train) | Métrica de solapamiento | Evaluación con dominios disjuntos (AUC 0,88) |
| `06` v1.0 | No guardaba las probabilidades de cada fold (imposible evaluar la fusión fuera de distribución) | Diseño del 07 | v1.1 (folds repetidos) |
| `07` | La rama URL de un fold podía quedar sin datos al excluir dominios | Prueba local | Guarda: rama neutra y registro del motivo |

---

## 7. Limitaciones conocidas

1. **Confusor temporal:** legítimo de 2002–2008 frente a phishing con mediana 2020–2024. Mitigado con el enmascarado de años; no eliminado.
2. **Ruido de etiquetas en phishing_pot:** 36 % de correos no phishing según la revisión manual (IC 95 %: 24,1–49,9). Explica parte de los errores spam→phishing de V3.
3. **Sesgo de tipo de correo:** el legítimo de CEAS son sobre todo listas de correo (términos `>`, `wrote`, `python`); "spamassassin" aparece en el 9 % de esa fuente.
4. **Solo inglés.** Correos generados con LLM no representados de forma explícita.
5. **Transformaciones opacas** de los CSV de Kaggle (CEAS, SpamAssassin): no auditables desde el crudo, salvo SpamAssassin (cotejo posible con los tarballs).
6. **Etiqueta débil en la rama URL:** cada URL hereda la clase de su correo; un phishing incluye URLs legítimas de la marca suplantada.
7. **`url_features` sin lista de sufijos públicos** (`co.uk` cuenta como un nivel más).
8. **El enmascarado de años** también reemplaza números como 2000 que no son años.
9. **No determinismo en GPU:** con las mismas semillas, el fold de Nigerian_Fraud dio 16,4 % y 12,1 % en dos corridas (los otros 3 folds, idénticos). Las cifras de ese fold tienen varianza no estimada.
10. **Meta-clasificador sobre validación:** 8.203 correos; sus cifras en la misma distribución son optimistas (ver 5).

---

## 8. Documentos de Semana 1–2 desalineados (resolución aditiva)

| Documento | Qué dice | Situación real |
|---|---|---|
| Checklist, Canvas, Ficha | 217.470 correos / "más de 200 mil" | 82.486 en Kaggle v1; 54.684 tras la preparación |
| Análisis de Datasets | Kaggle como fuente principal; Nazario ≈ 4.558 | Kaggle parcial (D2, D3); Nazario de Kaggle = 1.565, reemplazado por el crudo |
| Ficha, Canvas, Análisis de Datasets | Rama URL entrenada en PhiUSIIL | Variante B (D6) |
| Matriz de KPIs | Baselines 75/80 | Medidos: 98,7 / 96,2 |
| Semana 1 en general | TheHive | DFIR-IRIS (declarado en la Ficha de Semana 2) |
| Ficha de Semana 2 | Inferencia en HF Spaces CPU Basic (gratis) | Contenedor local en docker-compose (D12) |

---

## 9. Estado de los pendientes

- [x] Revisión manual de phishing_pot (50 correos).
- [x] Sprint 3: `06_distilbert` v1.1 y `07_fusion` (calibración, riesgo 0–100, Brier, ECE). Todo cupo en Colab T4.
- [x] Empaquetado: inferencia, contrato JSON y validación de punta a punta (08).
- [x] Archivos de referencia del contrato (`contracts/golden/`) versionados en el repositorio y validados en las pruebas.
- [x] API FastAPI cargando el modelo desde HF Hub (09 v2): salud ok, 21/21 válidas, 401 sin clave.
- [x] Stack local (IRIS + API + n8n + Wazuh) levantado y con conectividad verificada (14/10).
- [x] Flujo n8n (API → IRIS → Wazuh) y métricas de integración (KPI-1 y KPI-2).
- [x] Protocolo y medición del triaje manual frente al asistido (KPI-3, 18/10).
- [x] Workshops de la Semana 5 en `notebooks/04_optimizacion` y `05_evaluacion`, ejecutados con datos reales (19/10).
- [x] Interfaz web y validación externa con correos reales (D30 y D31, 20/10).

## Sprint 4 · Integración (13/10/2026)

| ID | Decisión | Justificación / evidencia |
|---|---|---|
| D23 | Flujo n8n v1.0 `G17 · Triaje de correo reportado`: Webhook → API → (IF) alerta DFIR-IRIS → evento Wazuh `POST /events`. Alerta IRIS solo para phishing, idioma no soportado y fallo de la API; spam/legítimo solo evento Wazuh. Claves por variables de entorno, nunca en el JSON | Workshop S4 (M4 el modelo sugiere y el analista decide; M5 fallo seguro a cola manual). Campos y severidades verificados en el código de iris-web v2.4.29 (`/alerts/add`, `/alerts/filter`; severidad 3–6 = Low–Critical, estado 2 = New). Probado con n8n 2.41.6 real y simuladores de API/IRIS/Wazuh: 5/5 casos con el comportamiento esperado (incluye bloqueo de IOC vivo). Falta la prueba con el stack real |
| D24 | KPI de integración y de triaje con scripts reproducibles (`lote_kpi.py`, `triaje_cronometro.py`) sobre 200 correos del test held-out (notebook 14); triaje en diseño cruzado 2 analistas × 20 correos, reportado como estimación con IC bootstrap | El baseline de negocio nunca se cronometró (riesgo 3 del proyecto). El diseño cruzado controla la dificultad de cada correo con solo dos analistas |
| D25 | API v1.1: calentamiento de las rutas en y es al arrancar | Prueba del stack real (14/10): 1.ª inferencia 8.920 ms (en) y 4.048 ms (es) por carga perezosa; la siguiente, 223 ms. Sin calentamiento, la demo y el lote de KPI medirían el arranque y no el servicio |
| H1 | Hallazgo (no se corrige): correo legítimo MUY corto en inglés ("Weekly report", 2 líneas) clasificado phishing con riesgo 19 | Umbral bajo por la política D9 (máximo recall con FPR ≤ 1 % en validación) y correos cortos poco representados en el corpus. Se mide el FPR real en el lote de 200 correos (D24); el analista decide (M4). Además la banda "alto" se asigna a toda clase phishing aunque el riesgo sea 19: a revisar con analistas |
| D26 | Flujo n8n v1.1: con `idioma_no_soportado` el correo va SIEMPRE a revisión manual (severidad Medium, sin etiqueta phishing) y el evento a Wazuh lleva `clase=no_fiable` para disparar la 100503 y no la 100501/100502 | Prueba real (14/10): correo en francés → phishing riesgo 91 "crítico" por el modelo inglés; la v1.0 lo titulaba "Phishing" con severidad Critical. Corregido y probado con simuladores |
| H2 | Hallazgo: correo corporativo legítimo moderno en inglés ("Q3 budget review", 5 líneas) → phishing riesgo 70. Con H1 son 2 de 2 legítimos corporativos sintéticos marcados | El legítimo del corpus (CEAS, SpamAssassin) es de listas técnicas antiguas: el FPR de test (0,9 %) no representa el correo de oficina. Se mide con 2.000 ham de Enron (notebook 15, A/B) antes de decidir un umbral operativo |
| E1 | Incidente: la interfaz web de IRIS dejó de responder (PR_CONNECT_ABORTED_ERROR) mientras la API interna `app:8000` seguía creando alertas | Resuelto con `docker compose restart nginx app`; todos los contenedores estaban arriba y con memoria holgada (no fue falta de RAM) |
| D27 | **Umbral operativo de la ruta inglesa = 0,8586** (variable `UMBRAL_EN`, inference v1.3). El umbral de validación 0,039 (D9) queda documentado como modo de "alta sensibilidad" | Notebook 15 (2.000 ham Enron, fuente nunca vista; umbral elegido en la mitad A y reportado en la B): con 0,039 el FPR en correo corporativo es **12,5 % (IC 95 % 10,6–14,7)** frente a 0,1 % en el test; con 0,8586 el FPR Enron-B es **1,3 % (0,8–2,2)** y el recall en todo el phishing del test es **95,97 %** (antes 99,73 %). Es el único punto de la curva que cumple a la vez FPR ≤ 2 % y recall ≥ 95 %. Limitación: el recall fuera de distribución (LOSO) se midió con 0,039 y no se puede recalcular con el modelo de producción; se espera menor |
| D28 | Flujo n8n v1.2: ids de severidad reales de IRIS v2.4.29 (1 = Medium por una migración; 4 = Low; 5 = High; 6 = Critical) | La alerta de revisión manual se mostró como *Low* con el id 4: el orden de creación de las severidades no es el del `post_init` |
| KPI-1 | **Alertas integradas = 100 % (83/83)**, verificado de forma independiente por la API de IRIS (+83 alertas G17). 200/200 correos procesados sin error HTTP. Latencia extremo a extremo (webhook → API → IRIS → Wazuh) p50 378 ms · p95 647 ms. En el flujo, con umbral 0,8586: en-phishing 58/60, en-legítimo 45/45, en-spam 44/45 (1 → legítimo), es 50/50 (texto_modelo preprocesado) | Lote del 14/10, notebook 14 + `lote_kpi.py`. Meta > 90 % cumplida |
| D29 | Flujo n8n v1.3: JWT de Wazuh reutilizado (datos estáticos del flujo) y estado `limitado_429`; `lote_kpi.py` con pausa de 2,1 s | Primer lote: solo 31 % de eventos llegó a Wazuh. Causa verificada en el código de Wazuh 4.14.8: `/events` admite 30 peticiones/min (`MAX_REQUESTS_EVENTS_DEFAULT`) y el login 50 intentos / 300 s; el flujo v1.0–1.2 hacía un login por correo. En operación (correos reportados por usuarios) el ritmo es muy inferior a 30/min. Probado con simuladores: 1 login para 41 correos y 429 detectado |
| KPI-2 | Lote repetido con flujo v1.3: **alertas integradas 100 % (83/83)**, **eventos Wazuh 100 % (200/200)**, conteo en `alerts.json` 70 → 270 (exacto), 0 errores HTTP, latencia extremo a extremo **p50 183 ms · p95 275 ms** | 14/10/2026 08:29 UTC. Cierra la integración (20 % del proyecto) con evidencia |
| KPI-3 (parcial) | Triaje, analista 1 (D. Salazar, ex-jefe de SOC), 20 correos: mediana manual 34,7 s (bloque A) vs asistido 21,8 s (bloque B) → −37,2 % (IC 95 % −26,7 a 73,1, no concluyente). Acierto 90 % manual vs 80 % asistido. Falta el analista 2: sin él, manual y asistido se comparan sobre correos DISTINTOS (dificultad confundida) | 14/10/2026. Observaciones: (1) el analista contradijo una sugerencia CORRECTA del modelo (FedEx, phishing 98 → "legítimo"): la supervisión humana también introduce errores; (2) dos correos etiquetados "legítimo" en SpaPhish (Correos de México con cobro aduanero, iCloud "actualiza tu pago") tienen rasgos claros de phishing: posible ruido de etiqueta en la fuente española, como en phishing_pot (64 % de etiquetas correctas). No verificado |
| KPI-3 | **Triaje N1 (cruzado, 2 perfiles × 20 correos, 40 registros)**: mediana manual 24,6 s vs asistido 16,6 s → **−32,4 % (IC 95 % −25,2 a 68,0; no concluyente, bajo la meta de 40 %)**. Acierto 70 % → **90 %**; phishing no detectado 25 % → **12,5 %**. Por perfil (derivado de las sesiones): experto (ex-jefe de SOC) 90 % → 80 % de acierto; no experto (desarrollador full stack, 10 años, sin triaje previo) 50 % → 100 % y phishing omitido 2/4 → 0/4 | 18/10/2026. Lectura: el beneficio medido de la IA es sobre todo de **exactitud en el usuario no experto**, más que de tiempo. Limitaciones: n = 20, 2 personas, perfiles distintos, posible ruido de etiqueta en SpaPhish (KPI-3 parcial). Se reporta como estimación |

## Cierre · Interfaz y validación externa (19 y 20/10/2026)

| ID | Decisión | Justificación / evidencia |
|---|---|---|
| D30 | Interfaz web en Streamlit como cliente de la API: no carga modelos, consulta `POST /v1/analizar` por la red interna y corre como servicio `ui` del mismo compose | Una sola implementación del modelo (la API) para la interfaz y para el SOC: lo que se muestra es exactamente lo que se evaluó. Probada con el modelo real: ejemplos en inglés y español, archivo .eml, historial, tema oscuro e idioma no soportado. 25 pruebas automáticas con un transporte simulado |
| D31 | Validación externa con cuatro correos reales de malware-traffic-analysis.net (05/05/2020) sin copiarlos: se registran su huella SHA-256, la clase y el riesgo | El sitio no publica una licencia que permita redistribuirlos y contienen URL maliciosas reales. Resultado: 4 de 4 phishing con riesgo crítico (98 a 100). Con n = 4 el IC 95 % de Wilson es 51–100 %: demostración cualitativa, no métrica (`results/metrics/validacion_externa_mta.json`) |
| H3 | Hallazgo (no se corrige): el extractor cuenta como URL la declaración DOCTYPE de HTML 4.01 (www[.]w3[.]org) y los enlaces `data-saferedirecturl` de Gmail | El entrenamiento usó el mismo extractor, así que la evaluación es coherente con la inferencia; cambiarlo ahora desalinearía el modelo desplegado. Se documenta en el manual y en las limitaciones |
| H4 | Hallazgo: con un archivo .eml la interfaz no muestra el aviso de texto corto | La longitud del texto solo se conoce después de que la API procesa el archivo. Dos de los cuatro correos reales tenían menos de 300 caracteres. Se documenta como limitación |
| D32 | La interfaz se publica como demostración en Streamlit Community Cloud, con el detector cargado dentro de la aplicación (`nube/streamlit_app.py` y `app/motor_local.py`); el despliegue local con la API y el SOC no cambia | Requisito de la evaluación (22/10): URL pública y activa. Opciones sugeridas verificadas el 22/10: Hugging Face Spaces exige PRO para Gradio y Docker en CPU desde julio de 2026 (coherente con el 402 de D12); Render gratis ofrece 0,1 CPU y 512 MB, insuficiente para PyTorch y DistilBERT; Streamlit Community Cloud ofrece hasta 2,7 GB. Mitigaciones del uso como oráculo: pesos privados leídos con un token de solo lectura guardado como secreto, 30 análisis por sesión, aviso de no usar correos reales y sin integración SOC. Reduce el riesgo, no lo elimina |
| D33 | La demostración en la nube usa Python 3.13, un token de Hugging Face propio de cada persona y de cada despliegue, y el historial de la interfaz registra la hora en UTC | Verificado el 22/10/2026 (`results/metrics/demo_nube_v1.json`): con Python 3.14 la instalación compilaba NumPy, pandas y scikit-learn desde el código fuente y no terminaba; con 3.13 tardó 23 s. Un token por persona permite revocar uno sin afectar a los demás, y todos se revocan al terminar la evaluación. El servidor de la nube corre en UTC, así que la columna de hora lo declara |
| H5 | Hallazgo (no se corrige): en un boletín comercial legítimo en HTML, la rama URL dio 99,8 % de phishing por enlaces de seguimiento, fuentes CSS y un píxel de apertura; la fusión lo clasificó como legítimo (riesgo 8) porque el DistilBERT dio 99,8 % legítimo | Es un solo caso y no se generaliza. Muestra el valor de la fusión frente a una sola rama y el mismo origen que H3: el extractor toma todas las URL del HTML, no solo los enlaces visibles. Cambiarlo ahora desalinearía el modelo de su entrenamiento |
