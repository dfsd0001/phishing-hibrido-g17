# Planificación del proyecto

Sistema inteligente de detección y clasificación de phishing híbrido (NLP y análisis de URL).
Proyecto Integrador de la Maestría en Inteligencia Artificial (MIAR0545), Universidad de
Especialidades Espíritu Santo (UEES). Grupo 17: Dennys Francisco Salazar Domínguez y Lenin Bolívar
González Rivadeneira.

Este documento resume la planificación aprobada en la Semana 1 (Canvas SMART, Cronograma Ágil y
Análisis de Stakeholders) y la contrasta con lo que ocurrió. Las decisiones técnicas que se citan con
un código (D1 a D29) están en la [bitácora de decisiones](bitacora_decisiones.md).

## 1. Problema

El phishing es la técnica de acceso inicial T1566 de MITRE ATT&CK y sigue siendo el punto de entrada
de buena parte de los incidentes de robo de credenciales y fraude. En un centro de operaciones de
seguridad (SOC), los correos que los empleados reportan como sospechosos llegan a una cola que los
analistas de nivel 1 revisan uno por uno. Ese triaje manual consume tiempo, genera fatiga de alertas
y depende de listas negras y reglas estáticas que no reconocen dominios recién creados ni textos
persuasivos nuevos. Los correos redactados con modelos de lenguaje elevan además la efectividad de
las campañas (Heiding et al., 2024).

El proyecto construye un sistema que clasifica cada correo como **legítimo, spam o phishing**, le
asigna un **riesgo de 0 a 100** que se puede leer como probabilidad y entrega el resultado en un
formato que el SOC puede consumir sin intervención manual.

## 2. Objetivos

**Objetivo general.** Entregar, en seis semanas, un detector híbrido que combine el análisis del
texto del correo con el análisis léxico de sus URL, calibrado, evaluado con honestidad fuera de la
distribución de entrenamiento e integrado de forma demostrable con herramientas de un SOC.

**Objetivos específicos y metas SMART** (Canvas SMART, 17/09/2026):

| Meta | Valor comprometido | Resultado medido | Estado |
|---|---|---|---|
| F1 macro de tres clases | 90 % o más | 98,7 % (IC 95 % 98,4 a 99,0) | Cumple |
| Recall de phishing | 95 % o más | 96,4 % (IC 95 % 95,4 a 97,3) | Cumple |
| Tasa de falsos positivos | 2 % o menos | 1,3 % en correo corporativo en inglés; 3,5 % en español nativo | Cumple en inglés; no cumple en español |
| Latencia por correo | Menos de 1 s | Percentil 95 de 275 ms de punta a punta | Cumple |
| Defanging de indicadores | 100 % | 0 indicadores vivos en 94.566 textos y en todas las salidas de la API | Cumple |
| Alertas integradas en el SOC | Más de 90 % | 100 % (83 de 83 alertas y 200 de 200 eventos) | Cumple |
| Reducción del tiempo de triaje N1 | 40 % o más | 32,4 %, IC 95 % de -25,2 a 68,0 (estimación con 20 correos) | No cumple; no concluyente |

Los valores de partida que figuraban en la Matriz de KPIs (F1 de 75 % y recall de 80 %) eran
estimaciones. La línea base se midió en el Sprint 2 (F1 98,7 %, recall 96,2 %) y desde entonces se
usa como referencia real. La fuente de cada valor está en
[`results/metrics/evaluacion_final.json`](../results/metrics/evaluacion_final.json) y en
[`results/metrics/kpi/`](../results/metrics/kpi/).

## 3. Relevancia

* **Para el SOC.** Prioriza la cola de correos reportados, extrae y defangea los indicadores y deja
  una alerta prellenada en el gestor de casos, de modo que el analista dedica su tiempo a los casos
  ambiguos.
* **Para la organización.** Detectar antes una campaña permite purgar buzones y bloquear dominios
  antes de que más personas entreguen sus credenciales.
* **Por costo.** Todo el sistema usa software libre y cómputo gratuito (presupuesto USD 0), por lo
  que es replicable por organizaciones que no pueden pagar pasarelas de correo comerciales.
* **Por qué inteligencia artificial.** Las reglas y listas dependen de indicadores conocidos. Un
  modelo aprende patrones de lenguaje (urgencia, suplantación) y de forma de las URL (subdominios,
  longitud, palabras sensibles) que se repiten en campañas nuevas, y un puntaje calibrado permite
  automatizar decisiones con umbrales explícitos.

## 4. Usuarios y partes interesadas

| Parte interesada | Papel | Qué necesita |
|---|---|---|
| Analistas SOC de nivel 1 | Usuarios principales | Un veredicto con nivel de confianza, una explicación mínima e indicadores defangeados |
| CISO o jefatura del SOC | Decide la adopción | Métricas fuera de distribución, tasa de falsos positivos controlada y costo de operación |
| Arquitecto de seguridad | Integra el sistema | Contrato de interfaz estable, latencia conocida y despliegue reproducible |
| Empleados que reportan correos | Titulares de los datos | Que su correo se procese con el mínimo de datos y sin salir de la organización |
| Docente del Proyecto Integrador | Patrocinador académico | Método CRISP-DM, decisiones documentadas y resultados verificables |

El análisis completo, con matriz de influencia e interés y plan de comunicación, está en el Análisis
de Stakeholders de la Semana 1. El impacto sobre cada grupo se analiza en
[consideraciones_eticas.md](consideraciones_eticas.md).

## 5. Alcance

**Incluye**

* Clasificación de correos en inglés y en español en tres clases, con riesgo de 0 a 100.
* Rama de texto (TF-IDF con regresión logística y DistilBERT) y rama de URL (XGBoost sobre variables
  léxicas calculadas solo a partir de la cadena).
* Fusión tardía con meta-clasificador calibrado y umbral operativo.
* Evaluación fuera de distribución (un corpus completo fuera del entrenamiento, periodo reciente,
  correo corporativo y español nativo) y análisis por subgrupos.
* API de inferencia, interfaz web e integración local con n8n, DFIR-IRIS y Wazuh.
* Defanging de todos los indicadores en datos, documentos y salidas.

**No incluye**

* Análisis de archivos adjuntos, imágenes o códigos QR.
* Resolución de dominios, visita de URL, capturas de páginas o análisis dinámico en sandbox: las URL
  nunca se resuelven ni se visitan.
* Encabezados de autenticación (SPF, DKIM, DMARC) y reputación del remitente.
* Idiomas distintos del inglés y del español: se marcan para revisión manual.
* Acciones automáticas sobre buzones (purga, bloqueo) o cierre automático de alertas: el sistema
  sugiere y el analista decide.
* Operación en producción con correo real de una organización. La demostración pública en la nube
  existe para la evaluación y se usa solo con ejemplos o correos de prueba.

## 6. Metodología de trabajo

El proyecto siguió CRISP-DM dentro de cuatro sprints de Scrum. Los dos integrantes compartieron los
roles de científico de datos e ingeniero de aprendizaje automático; Dennys Salazar actuó como líder
técnico y Lenin González como dueño del producto. El reparto de esfuerzo fijado al inicio fue de
80 % para datos, modelado y evaluación, y 20 % para la integración.

| Fase CRISP-DM | Dónde se documenta |
|---|---|
| Comprensión del negocio | Este documento y los entregables de la Semana 1 |
| Comprensión de los datos | [analisis_datos.md](analisis_datos.md), `notebooks/01_exploracion.ipynb` |
| Preparación de los datos | [analisis_datos.md](analisis_datos.md), `notebooks/02_preprocesamiento.ipynb` |
| Modelado | [arquitectura.md](arquitectura.md), `notebooks/03_modelado.ipynb`, [optimizacion.md](optimizacion.md) |
| Evaluación | `notebooks/05_evaluacion.ipynb`, [consideraciones_eticas.md](consideraciones_eticas.md) |
| Despliegue | [arquitectura.md](arquitectura.md), [manual_usuario.md](manual_usuario.md), `deploy/README.md` |

## 7. Cronograma: planificado frente a real

El cronograma aprobado tenía seis semanas (14/09 a 25/10/2026) en cuatro sprints: Sprint 1 de
investigación y diseño (semana 1), Sprint 2 de datos y línea base (semanas 2 y 3), Sprint 3 de
modelado y validación (semanas 4 y 5) y Sprint 4 de integración y documentación (semana 6).

| Hito del Canvas SMART | Fecha planificada | Fecha real | Observación |
|---|---|---|---|
| Objetivos SMART, estado del arte y datasets | 20/09 | 20/09 | Ocho entregables de la Semana 1 |
| EDA y reporte de calidad de datos | 27/09 | 02/10 | Cinco días de retraso; se entregó junto con la línea base. No movió ninguna meta |
| Modelo base funcional | 04/10 | 02/10 | Línea base medida: F1 98,7 % y recall 96,2 % |
| Modelo optimizado y API | 11/10 | 03/10 | DistilBERT, rama URL, fusión V3 calibrada y API cargando el modelo desde Hugging Face Hub |
| Validación y plan de pruebas | 18/10 | 14/10 a 19/10 | Correo corporativo (14/10), triaje cronometrado (18/10) y Workshops de la Semana 5 (19/10) |
| Producción limitada | 22/10 | 14/10 | API, n8n, DFIR-IRIS y Wazuh integrados en local; 100 % de alertas integradas |
| Demostración final y documentación | 25/10 | 20/10 | Interfaz web, validación con correos reales y documentación; publicación tras la revisión del equipo |

**Trabajo no planificado.** Dos cambios entraron durante el proyecto y se absorbieron con el tiempo
ganado al adelantar el Sprint 3:

1. **Ruta en español** (decisiones D13 a D22, hasta el 08/10). El cronograma declaraba el
   multilingüismo fuera de alcance. Se incorporó porque la primera prueba de la API clasificó como
   phishing un correo legítimo en español y el contexto de uso previsto es una organización
   ecuatoriana. Se limitó a una ruta propia con sus métricas y su limitación documentada (FPR de
   3,5 %).
2. **Umbral operativo** (D27, 14/10). La prueba con correo corporativo real mostró 12,5 % de falsos
   positivos con el umbral de validación, y se fijó un umbral operativo elegido con datos que el
   modelo nunca vio.

## 8. Recursos

**Datos.** Corpus públicos de correos en inglés (CEAS 2008, SpamAssassin, Nigerian Fraud, Nazario,
phishing_pot), corpus nativos en español (SpaPhish y SpearPhishMX), correo corporativo de Enron para
validar falsos positivos y URL de PhiUSIIL y PhishTank como evidencia auxiliar. Fuentes, licencias y
huellas en [`data/README.md`](../data/README.md).

**Hardware.**

| Uso | Recurso |
|---|---|
| Ajuste fino de DistilBERT y evaluación | Google Colab con GPU T4 (gratuito) |
| Preparación de datos, línea base, rama URL y optimización | CPU de Colab o local |
| Despliegue del SOC local | Equipo con Docker Desktop y 12 GB de memoria asignados: DFIR-IRIS cerca de 2,5 GB, API hasta 3 GB, Wazuh hasta 2 GB, n8n hasta 1 GB e interfaz hasta 512 MB |

**Software.** Python 3.13, PyTorch 2.11, Transformers 5.17, scikit-learn 1.6.1, XGBoost 3.4.1,
Optuna 5.0, Fairlearn 0.14, FastAPI 0.143, Streamlit 1.66, n8n 2.41.6, DFIR-IRIS 2.4.29 y Wazuh
4.14.8. La lista completa con versiones fijadas está en [arquitectura.md](arquitectura.md).

**Presupuesto.** USD 0. Todo el software es libre y el cómputo, gratuito. Los artefactos del modelo
se alojan en un repositorio privado de Hugging Face Hub, también gratuito.

## 9. Riesgos y mitigación

| Riesgo identificado al inicio | Qué ocurrió | Mitigación aplicada |
|---|---|---|
| La clase podía ser un artefacto de la fuente | Se confirmó: un clasificador predice el corpus de origen con F1 de 0,81 a partir del texto | Al menos dos corpus por clase, pliegues con un corpus completo fuera del entrenamiento y selección del modelo por esos pliegues (D10) |
| Desplazamiento de dominio en la rama URL | Cerca de 70 % de los correos de cada clase tiene URL; las URL de PhiUSIIL tenían un artefacto de ruta y no transferían a correo (AUC 0,67) | Rama URL entrenada con URL de correos y dominios disjuntos (D6); en español se excluyó porque no supera el azar (D21) |
| Línea base de negocio sin medir | El tiempo de triaje manual no existía | Medición cruzada con dos perfiles de analista y 20 correos; se reporta como estimación con intervalo de confianza |
| Acceso a fuentes (registro de PhishTank cerrado) | No se pudo usar la API de PhishTank | Copia pública con commit fijado, solo para validación externa |
| Límites de cómputo en Colab | Todo el entrenamiento cupo en una T4 | Puntos de control en Drive; DistilBERT no se optimizó por costo (13 h estimadas para 60 pruebas) |
| Ampliación del alcance | Entró la ruta en español | Ruta separada, con métricas y limitaciones propias, sin mover las metas del inglés |
| Desempeño bajo la meta | Las metas se cumplieron en la partición aleatoria, pero el correo corporativo mostró 12,5 % de falsos positivos | Umbral operativo elegido en una mitad de los datos y reportado en la otra (D27) |
| Infraestructura de inferencia | Hugging Face Spaces dejó de ofrecer contenedores gratuitos (respuesta 402 al crear el Space) | API en un contenedor local dentro de la red del SOC (D12); los correos no salen de la organización |
| URL pública para la evaluación (requisito agregado en la semana 6) | Hugging Face Spaces exige PRO y Render ofrece 512 MB de RAM | Demostración en Streamlit Community Cloud con el modelo dentro de la interfaz (D32) |
| Licencia del gestor de casos | TheHive exige una licencia validada por su fabricante | DFIR-IRIS, libre y sin licencia, declarado en la Ficha de la Semana 2 |

## 10. Coherencia con los entregables anteriores

Algunos documentos de las semanas 1 y 2 describen decisiones que cambiaron después. No se rehicieron;
la situación vigente es la de este repositorio:

| Documento | Qué dice | Situación vigente |
|---|---|---|
| Canvas, Checklist y Ficha de la Semana 2 | 217.470 correos | 82.486 en los archivos de Kaggle usados; 54.684 en el dataset final en inglés |
| Ficha, Canvas y Análisis de Datasets | Rama URL entrenada con PhiUSIIL | URL extraídas de los correos (D6) |
| Documentos de la Semana 1 | TheHive como gestor de casos | DFIR-IRIS |
| Ficha de la Semana 2 | Inferencia en Hugging Face Spaces | Contenedor local (D12) |
| Matriz de KPIs | Línea base estimada de 75 % y 80 % | Línea base medida de 98,7 % y 96,2 % |

## Referencias

* Heiding, F., Schneier, B., Vishwanath, A., Bernstein, J. y Park, P. S. (2024). Devising and
  detecting phishing emails using large language models. *IEEE Access, 12*, 42131-42146.
  https://doi.org/10.1109/ACCESS.2024.3375882
* MITRE. T1566: Phishing. MITRE ATT&CK. https://attack.mitre.org/techniques/T1566/
