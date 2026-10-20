# Resumen de resultados

Reporte generado a partir de `results/metrics/`. Partición de prueba en inglés: 8.203 correos que no
intervinieron en ninguna decisión de entrenamiento, calibración ni umbral. Intervalos de confianza al
95 % por bootstrap de percentiles (2.000 remuestreos), salvo que se indique otro método.

## 1. Metas SMART

| Meta | Resultado | Fuente | Cumple |
|---|---|---|---|
| F1 macro >= 0,90 | 0,9869 [0,9841; 0,9895] | prueba, umbral operativo | Sí |
| Recall de phishing >= 95 % | 0,9637 [0,9539; 0,9726] | prueba, umbral operativo | Sí |
| FPR <= 2 % (inglés, correo corporativo) | 1,3 % IC [0,8; 2,2] | Enron, notebook 15 | Sí |
| FPR <= 2 % (español nativo) | 3,5 % | prueba española | No |
| Latencia < 1 s | p95 275 ms de punta a punta | lote KPI, 200 correos | Sí |
| Alertas integradas > 90 % | 100,0 % | lote KPI, IRIS y Wazuh | Sí |
| Reducción del triaje N1 >= 40 % | 32,4 % IC [-25,2; 68,0] (estimación) | 20 correos, 2 analistas | No |

## 2. Comparación con la línea base y el piso de referencia

| Modelo | F1 macro | Recall de phishing | Precisión de phishing | FPR de phishing |
|---|---|---|---|---|
| Piso (estratificado) | 0,3344 [0,3240; 0,3440] | 19,6 % [17,6 %; 21,6 %] | 19,3 % [17,3 %; 21,2 %] | 18,21 % [17,33 %; 19,16 %] |
| Línea base TF-IDF | 0,9870 [0,9843; 0,9896] | 98,3 % [97,6 %; 99,0 %] | 97,5 % [96,7 %; 98,3 %] | 0,55 % [0,39 %; 0,74 %] |
| DistilBERT | 0,9899 [0,9875; 0,9923] | 98,7 % [98,1 %; 99,3 %] | 97,9 % [97,2 %; 98,6 %] | 0,46 % [0,31 %; 0,63 %] |
| Fusión V3, umbral de validación | 0,9874 [0,9846; 0,9900] | 99,7 % [99,3 %; 99,9 %] | 96,0 % [95,0 %; 97,0 %] | 0,91 % [0,69 %; 1,14 %] |
| Fusión V3, umbral operativo | 0,9869 [0,9841; 0,9895] | 96,4 % [95,4 %; 97,3 %] | 99,1 % [98,6 %; 99,5 %] | 0,19 % [0,10 %; 0,31 %] |

Prueba exacta de McNemar sobre los mismos correos (solo cuentan los casos en que discrepan):

| A | B | Acierta solo A | Acierta solo B | p |
|---|---|---:|---:|---:|
| Línea base TF-IDF | Fusión V3, umbral operativo | 36 | 39 | 0,818 |
| DistilBERT | Fusión V3, umbral operativo | 51 | 33 | 0,063 |
| Fusión V3, umbral de validación | Fusión V3, umbral operativo | 49 | 47 | 0,919 |

Ninguna diferencia es significativa al 5 %: en la partición aleatoria, los tres modelos superan 0,98
de F1 y ninguno es claramente superior en exactitud global.

| Modelo | AUC-ROC | AUC-PR | Brier | ECE |
|---|---:|---:|---:|---:|
| Línea base TF-IDF | 0,9990 | 0,9948 | No medido | No medido |
| DistilBERT | 0,9994 | 0,9975 | 0,0153 | 0,0052 |
| Fusión V3 | 0,9987 | 0,9959 | 0,0111 | 0,0055 |

## 3. Phishing de fuentes y periodos no vistos

Recall de phishing cuando la fuente o el periodo completo queda fuera del entrenamiento (umbral con FPR
de hasta 1 % en validación de cada pliegue).

| Pliegue | V0: línea base | V1: DistilBERT | V2: DistilBERT y URL | V3: las tres ramas |
|---|---:|---:|---:|---:|
| loso_phishing_pot | 68,5 % | 73,6 % | 83,5 % | 83,5 % |
| loso_Nigerian_Fraud | 91,7 % | 84,8 % | 67,8 % | 94,1 % |
| loso_nazario_anual | 95,5 % | 96,3 % | 96,3 % | 97,4 % |
| temporal_phishing_2025+ | 93,3 % | 94,1 % | 97,9 % | 98,6 % |

## 4. Subgrupos (umbral operativo)

| Dimensión | Subgrupo | Recall de phishing | FPR | Correos |
|---|---|---:|---:|---:|
| Corpus | CEAS_08 |  | 0,05 % | 5.844 |
| Corpus | Nigerian_Fraud | 94,5 % |  | 493 |
| Corpus | SpamAssasin |  | 1,15 % | 871 |
| Corpus | nazario_anual | 98,9 % |  | 439 |
| Corpus | phishing_pot | 96,0 % |  | 556 |
| Longitud (caracteres) | 300 a 2.000 | 98,6 % | 0,15 % | 4.214 |
| Longitud (caracteres) | < 300 | 93,2 % | 0,00 % | 1.909 |
| Longitud (caracteres) | > 2.000 | 94,0 % | 0,52 % | 2.080 |
| URL | con URL | 97,0 % | 0,15 % | 5.736 |
| URL | sin URL | 94,4 % | 0,29 % | 2.467 |
| Antigüedad | 2010 a 2019 | 99,5 % | 0,00 % | 213 |
| Antigüedad | 2020 o después | 96,7 % |  | 775 |
| Antigüedad | antes de 2010 | 94,3 % | 0,19 % | 7.119 |
| Antigüedad | sin fecha | 96,2 % | 0,00 % | 96 |

## 5. Ruta en español (prueba nativa)

| Conjunto | Correos | Recall de phishing | FPR |
|---|---:|---|---|
| Total | 641 | 93,5 % [90,6 %; 95,6 %] | 3,5 % [1,9 %; 6,6 %] |
| SpaPhish | 202 | 89,7 % [82,5 %; 94,2 %] | 9,5 % [5,1 %; 17,0 %] |
| SpearPhishMX | 439 | 95,0 % [91,8 %; 97,0 %] | 0,0 % [0,0 %; 2,4 %] |

## 6. Escenarios de estrés (Workshop 1)

| Escenario | Nivel | Recall | Precisión | FPR | Caída de recall (puntos) | Veredicto |
|---|---|---:|---:|---:|---:|---|
| Referencia | sin perturbar | 95,9 % | 98,9 % | 0,24 % | 0,0 | OK |
| A. Ruido | 2 % de letras | 95,3 % | 98,8 % | 0,26 % | 0,5 | OK |
| A. Ruido | 5 % de letras | 95,3 % | 98,7 % | 0,28 % | 0,5 | OK |
| A. Ruido | 10 % de letras | 93,7 % | 98,6 % | 0,31 % | 2,2 | OK |
| B. Ofuscación | palabras sensibles | 95,0 % | 98,9 % | 0,24 % | 0,8 | OK |
| C. Información incompleta | 1000 caracteres | 96,1 % | 98,9 % | 0,24 % | -0,3 | OK |
| C. Información incompleta | 300 caracteres | 90,1 % | 98,8 % | 0,24 % | 5,8 | FALLA |
| D. Rama URL caída | bloque URL neutro | 90,9 % | 99,1 % | 0,18 % | 5,0 | OK |
| E. Sin enlaces | sin URL en texto ni rama | 92,0 % | 99,1 % | 0,18 % | 3,9 | OK |
| F. Desbalance | 10 % de phishing | 96,4 % | 98,0 % | 0,21 % | -0,5 | OK |
| F. Desbalance | 5 % de phishing | 96,4 % | 96,2 % | 0,20 % | -0,5 | OK |
| F. Desbalance | 1 % de phishing | 96,4 % | 83,7 % | 0,19 % | -0,5 | OK |
| G. Cambio de distribución | loso_phishing_pot | 83,5 % |  | 0,95 % | 12,3 | FALLA |
| G. Cambio de distribución | loso_Nigerian_Fraud | 94,1 % |  | 1,10 % | 1,8 | OK |
| G. Cambio de distribución | loso_nazario_anual | 97,4 % |  | 0,97 % | -1,6 | OK |
| G. Cambio de distribución | temporal_phishing_2025+ | 98,6 % |  | 1,01 % | -2,7 | OK |
| G. Cambio de distribución | correo corporativo (Enron) | 96,0 % |  | 1,30 % | -0,1 | OK |
| G. Cambio de distribución | español nativo | 93,5 % |  | 3,54 % | 2,3 | FALLA |

## 7. Integración con el SOC

Lote de 200 correos de prueba enviados por el flujo de n8n el 2026-10-14:

| Indicador | Valor |
|---|---|
| Respuestas sin error | 200 de 200 |
| Alertas integradas en DFIR-IRIS | 83 de 83 (100,0 %) |
| Eventos entregados a Wazuh | 100,0 % |
| Latencia de extremo a extremo | p50 183 ms, p95 275 ms |

Triaje de nivel 1. Es una estimación con 20 correos y dos perfiles de analista, uno experto y otro
sin experiencia previa en triaje (diseño cruzado, 40 registros):

| Indicador | Manual | Asistido |
|---|---:|---:|
| Tiempo mediano por correo | 24,6 s | 16,6 s |
| Acierto | 70 % | 90 % |
| Phishing no detectado | 25,0 % | 12,5 % |

Reducción del tiempo: 32,4 % (IC 95 % -25,2 a 68,0). Es una
estimación: el intervalo incluye valores negativos y no permite afirmar que se cumple la meta de 40 %.

## 8. Validación con correos reales

Fuente: 2020-05-05 - 4 examples of phishing emails with fake login pages (https://www.malware-traffic-analysis.net/2020/05/05/index.html). Los correos no se redistribuyen.

| Archivo | SHA-256 (inicio) | Clase | Riesgo | Latencia |
|---|---|---|---:|---:|
| 2020-05-05-phishing-email-example-01.eml | `2c76b313c0313795` | phishing | 100 | 73 ms |
| 2020-05-05-phishing-email-example-02.eml | `de6336f347a7c26d` | phishing | 100 | 364 ms |
| 2020-05-05-phishing-email-example-03.eml | `147062cf2eaa92bb` | phishing | 98 | 79 ms |
| 2020-05-05-phishing-email-example-04.eml | `b264818bdfa95e04` | phishing | 100 | 104 ms |

Los cuatro correos se clasifican como phishing con riesgo crítico. Con cuatro casos el intervalo de confianza va de 51 % a 100 %, de modo que es una demostración cualitativa de que el sistema funciona con correos reales y no una métrica; las métricas del proyecto son las de results/metrics/evaluacion_final.json.
