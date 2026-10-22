"""Textos de la interfaz en español e inglés, correos de ejemplo y métricas del modelo.

Los ejemplos se escriben defangeados (``hxxps[://]dominio[.]example``), igual que en toda la
documentación del proyecto, y usan dominios reservados para documentación (RFC 2606 y 6761).
La API acepta texto defangeado: las URL se refangan solo en memoria para calcular variables.

Las métricas de la sección "Acerca del modelo" provienen de ``results/metrics`` (evaluación
final del notebook ``05_evaluacion``, correo corporativo del notebook 15 y KPI de integración);
``tests/test_app.py`` comprueba que coincidan con esos archivos.
"""

from __future__ import annotations

COLORES_CLASE = {"legitimo": "#2a78d6", "spam": "#eb6834", "phishing": "#1baf7a"}

EJEMPLOS = {
    "phishing_en": {
        "es": "Phishing en inglés (suplantación bancaria)",
        "en": "Phishing in English (bank impersonation)",
        "asunto": "Your account has been suspended",
        "cuerpo": (
            "Dear customer,\n\nWe detected unusual sign-in activity on your online banking account. To avoid "
            "permanent suspension, verify your identity within 24 hours at "
            "hxxps[://]secure-login[.]bank-example[.]test/verify?id=7\n\nIf you do not confirm your password, "
            "your account and cards will be closed.\n\nSecurity Department"
        ),
    },
    "legitimo_en": {
        "es": "Legítimo en inglés (acta de reunión)",
        "en": "Legitimate in English (meeting minutes)",
        "asunto": "Minutes of Tuesday's project meeting",
        "cuerpo": (
            "Hi team,\n\nAttached are the minutes from Tuesday's meeting. Please review the action items assigned "
            "to you before Friday and add your comments to the shared document. The next meeting is scheduled for "
            "Monday at 10:00 in room 3.\n\nThanks,\nMaria"
        ),
    },
    "spam_en": {
        "es": "Spam en inglés (oferta comercial)",
        "en": "Spam in English (commercial offer)",
        "asunto": "Limited offer: 70% off premium watches",
        "cuerpo": (
            "Exclusive deal for you! Buy premium replica watches today with free worldwide shipping. Limited "
            "stock, order now at hxxp[://]shop-deals[.]example[.]com and get a second watch free!!! "
            "To unsubscribe, reply STOP."
        ),
    },
    "phishing_es": {
        "es": "Phishing en español (bloqueo de cuenta)",
        "en": "Phishing in Spanish (account lock)",
        "asunto": "Aviso: su cuenta será bloqueada",
        "cuerpo": (
            "Estimado cliente:\n\nDetectamos un intento de acceso no autorizado a su banca en línea. Para evitar el "
            "bloqueo de su cuenta, actualice sus datos en las próximas 24 horas ingresando a "
            "hxxps[://]banca-segura[.]example[.]com/validar\n\nSi no realiza la verificación, su tarjeta será "
            "suspendida.\n\nAtentamente,\nDepartamento de Seguridad"
        ),
    },
    "otro_idioma": {
        "es": "Otro idioma (francés): requiere revisión manual",
        "en": "Other language (French): needs manual review",
        "asunto": "Votre compte a été suspendu",
        "cuerpo": (
            "Bonjour,\n\nNous avons détecté une activité inhabituelle sur votre compte. Veuillez confirmer vos "
            "informations dans les 24 heures sur hxxps[://]verification[.]example[.]org afin d'éviter la "
            "suspension définitive.\n\nService clients"
        ),
    },
}

# Valores de results/metrics/evaluacion_final.json (prueba, umbral operativo), fpr_enron_v1.json y
# kpi/kpi_resumen.json. Las pruebas verifican que coincidan con esos archivos.
METRICAS = {
    "f1_macro": 0.9869,
    "recall_phishing": 0.9637,
    "precision_phishing": 0.9910,
    "fpr_phishing": 0.0019,
    "fpr_enron_pct": 1.3,
    "recall_espanol": 0.9354,
    "fpr_espanol": 0.0354,
    "latencia_p95_ms": 275,
    "correos_prueba": 8203,
}

LONGITUD_CORTA = 300

TEXTOS = {
    "es": {
        "titulo": "Detector híbrido de phishing",
        "subtitulo": (
            "Clasifica un correo como legítimo, spam o phishing y calcula un riesgo de 0 a 100 combinando el "
            "análisis del texto (DistilBERT y TF-IDF) con el de sus URL. Grupo 17, Maestría en Inteligencia "
            "Artificial, UEES."
        ),
        "idioma": "Idioma de la interfaz",
        "estado": "Estado del servicio",
        "estado_ok": "API disponible",
        "estado_cargando": "La API responde, pero el modelo aún se está cargando",
        "estado_caido": "La API no responde",
        "estado_ok_nube": "Modelo disponible",
        "estado_cargando_nube": (
            "Cargando el modelo. En la primera visita tarda unos minutos; después pulse Analizar de nuevo."
        ),
        "estado_sin_modelo": "No se pudo cargar el modelo. Avise al equipo del proyecto.",
        "inferencia_nube": "demostración en la nube",
        "privacidad_nube": (
            "Demostración pública alojada en Streamlit Community Cloud (servidores en Estados Unidos). El correo se "
            "analiza en memoria y no se guarda, pero no pegue correos reales con datos personales: use los "
            "ejemplos o correos de prueba."
        ),
        "error_limite": "Llegó al límite de {n} análisis de esta sesión de demostración.",
        "privacidad": (
            "El correo se envía solo a la API del detector, que no lo guarda. El historial existe únicamente en "
            "esta sesión del navegador y se borra al cerrarla."
        ),
        "pestana_analizar": "Analizar",
        "pestana_historial": "Historial",
        "pestana_acerca": "Acerca del modelo",
        "pestana_ayuda": "Ayuda",
        "ejemplo": "Correo de ejemplo",
        "boton_ejemplo": "Probar con un ejemplo",
        "modo_texto": "Pegar el texto",
        "modo_eml": "Subir un archivo .eml",
        "asunto": "Asunto",
        "cuerpo": "Cuerpo del correo",
        "ayuda_cuerpo": "Puede pegar texto o HTML. Las URL pueden estar defangeadas (hxxps[://]...).",
        "archivo": "Archivo .eml (máximo 1,5 MB)",
        "prioridad_eml": "Si sube un archivo, se analiza el archivo y no el texto pegado.",
        "caracteres": "caracteres",
        "boton_analizar": "Analizar",
        "boton_limpiar": "Limpiar",
        "procesando": "Analizando el correo...",
        "error_vacio": "Escriba el asunto o el cuerpo del correo, o suba un archivo .eml.",
        "error_asunto_largo": "El asunto supera los 1.000 caracteres.",
        "error_cuerpo_largo": "El cuerpo supera los 500.000 caracteres.",
        "error_eml_grande": "El archivo supera 1,5 MB.",
        "error_sin_conexion": (
            "No se pudo conectar con la API del detector. Verifique que el servicio esté levantado "
            "(docker compose up -d) y que G17_API_URL apunte a él."
        ),
        "error_tiempo_agotado": "La API tardó demasiado en responder. Intente de nuevo en unos segundos.",
        "error_clave_invalida": "La API rechazó la clave. Revise la variable G17_API_KEY de la interfaz.",
        "error_modelo_no_disponible": (
            "El modelo todavía se está cargando (la primera vez puede tardar unos minutos). Intente de nuevo."
        ),
        "error_entrada_invalida": "La API rechazó el contenido enviado. Revise que el archivo sea un .eml válido.",
        "error_error_servidor": "La API tuvo un error interno. El análisis no se completó.",
        "error_respuesta_invalida": "La API devolvió una respuesta que no cumple el contrato.",
        "aviso_corto": (
            "El texto tiene menos de {n} caracteres. En la evaluación, el detector encontró el 93 % del phishing "
            "corto frente al 96 % del total: revise el resultado con más cuidado."
        ),
        "aviso_idioma": (
            "Idioma no soportado ({idioma}): el modelo solo está entrenado para inglés y español. "
            "El resultado no es fiable y el correo debe revisarse manualmente."
        ),
        "resultado": "Resultado",
        "clase": "Clase",
        "riesgo": "Riesgo",
        "nivel": "Nivel",
        "probabilidades": "Probabilidad de cada clase",
        "ramas": "Detalle de las ramas del modelo",
        "rama": "Rama",
        "rama_bert": "Texto, DistilBERT",
        "rama_base": "Texto, TF-IDF",
        "rama_url": "URL (máximo de sus puntajes)",
        "sin_url": "El correo no tiene URL; la rama URL usa un valor neutro.",
        "no_aplica": "No aplica en esta ruta",
        "iocs": "Indicadores encontrados (defangeados)",
        "sin_iocs": "No se encontraron URL ni direcciones IP.",
        "mitre": "Técnicas MITRE ATT&CK",
        "ruta": "Ruta del modelo",
        "idioma_detectado": "Idioma detectado",
        "latencia": "Tiempo de análisis",
        "umbral": "Umbral de phishing",
        "recomendacion": "Qué hacer",
        "rec_phishing": (
            "No abra enlaces ni adjuntos ni responda. Reporte el correo al equipo de seguridad usando el canal "
            "de reporte de su organización."
        ),
        "rec_spam": "Correo no deseado. Puede eliminarlo o marcarlo como spam.",
        "rec_legitimo": (
            "No se encontraron señales de phishing. La decisión final corresponde a la persona; ante cualquier "
            "duda, verifique con el remitente por otro canal."
        ),
        "rec_revision": "Este resultado requiere revisión manual por un analista.",
        "descargar_json": "Descargar el resultado (JSON)",
        "historial_vacio": "Todavía no hay análisis en esta sesión.",
        "descargar_csv": "Descargar el historial (CSV)",
        "limpiar_historial": "Borrar el historial",
        "comparacion": "Comparación de los análisis de la sesión",
        "metrica": "Métrica",
        "valor": "Valor",
        "hora": "Hora",
        "nombres_clase": {"legitimo": "Legítimo", "spam": "Spam", "phishing": "Phishing"},
        "nombres_nivel": {"bajo": "Bajo", "medio": "Medio", "alto": "Alto", "critico": "Crítico"},
        "acerca": """
### Cómo funciona

El detector combina tres ramas mediante fusión tardía:

1. **DistilBERT** ajustado sobre 38.278 correos en inglés lee el texto completo (hasta 256 tokens).
2. **TF-IDF con regresión logística** sobre palabras y caracteres, una línea base interpretable.
3. **XGBoost sobre la forma de cada URL** (longitud, símbolos, palabras sensibles, dominio de primer
   nivel), calculada sin visitar el enlace.

Un meta-clasificador calibrado combina las tres salidas y produce la probabilidad de cada clase; el
riesgo es 100 veces la probabilidad de phishing. Los correos en español usan un DistilBERT
multilingüe. Cualquier otro idioma se marca para revisión manual.

### Desempeño medido
""",
        "tabla_metricas": {
            "F1 macro (prueba, 8.203 correos en inglés)": "{f1_macro:.4f}",
            "Recall de phishing (prueba)": "{recall_phishing:.1%}",
            "Precisión de phishing (prueba)": "{precision_phishing:.1%}",
            "Falsos positivos de phishing (prueba)": "{fpr_phishing:.2%}",
            "Falsos positivos en correo corporativo real (Enron)": "{fpr_enron_pct} %",
            "Recall de phishing en español nativo": "{recall_espanol:.1%}",
            "Falsos positivos en español nativo": "{fpr_espanol:.1%}",
            "Latencia de punta a punta (percentil 95)": "{latencia_p95_ms} ms",
        },
        "limitaciones": """
### Limitaciones y advertencias

* **Apoyo, no decisión.** El resultado orienta al analista; no debe bloquear ni borrar correos sin
  revisión humana.
* **Correos cortos o sin URL.** El recall baja a 93 % en textos de menos de 300 caracteres y a 94 % en
  correos sin URL.
* **Campañas nuevas.** Con una fuente de phishing nunca vista, el recall bajó a 84 % en la evaluación.
  El modelo necesita reentrenamiento periódico.
* **Español.** Los falsos positivos (3,5 %) superan la meta de 2 %; los positivos en español deben
  confirmarse.
* **Otros idiomas.** No están soportados: el resultado no es fiable.
* **Datos de entrenamiento.** Corpus públicos de 1998 a 2026 en inglés, más SpaPhish y SpearPhishMX en
  español; no representan el correo de una organización concreta.

### Uso aceptable

La herramienta está pensada para equipos de seguridad y usuarios que reportan correos sospechosos. No
debe usarse para analizar correo ajeno sin autorización ni para probar variantes de un correo de
phishing hasta evadir la detección. Los indicadores se muestran siempre defangeados y la herramienta
nunca visita los enlaces.
""",
        "ayuda": """
### Uso paso a paso

1. Pegue el asunto y el cuerpo del correo, o suba el archivo .eml (en la mayoría de los clientes de
   correo: *Descargar mensaje* o *Guardar como*).
2. Pulse **Analizar**. El resultado aparece en uno o dos segundos.
3. Revise la clase, el riesgo y los indicadores. La recomendación indica qué hacer.
4. Descargue el resultado en JSON o el historial de la sesión en CSV si necesita adjuntarlo a un reporte.

Para probar sin un correo propio, elija un ejemplo y pulse **Probar con un ejemplo**.

### Problemas frecuentes

| Mensaje | Causa | Solución |
|---|---|---|
| No se pudo conectar con la API | El servicio no está levantado | `docker compose up -d` en la carpeta `deploy` |
| El modelo se está cargando | Primera descarga del modelo | Esperar de 2 a 4 minutos |
| La API rechazó la clave | Claves distintas en la API y la interfaz | Revisar `API_KEY` en `deploy/.env` |
| Idioma no soportado | Correo en un idioma distinto de inglés o español | Revisión manual |

### Preguntas frecuentes

**¿Se guarda el correo?** No. La API no lo almacena y el historial vive solo en esta sesión.

**¿Se visitan los enlaces?** No. Las URL se analizan solo por su forma.

**¿Qué significa un riesgo de 85?** Que el modelo estima una probabilidad de phishing de 0,85. El
umbral operativo es 0,86: por encima, el correo se clasifica como phishing.

**¿Cómo cambio entre tema claro y oscuro?** En el menú de tres puntos (arriba a la derecha): *System*, *Light* o
*Dark*. Por defecto la interfaz sigue la preferencia del sistema operativo.

Soporte: repositorio del proyecto en GitHub (sección *Issues*).
""",
    },
    "en": {
        "titulo": "Hybrid phishing detector",
        "subtitulo": (
            "Classifies an email as legitimate, spam or phishing and computes a 0 to 100 risk score by "
            "combining text analysis (DistilBERT and TF-IDF) with analysis of its URLs. Group 17, Master's in "
            "Artificial Intelligence, UEES."
        ),
        "idioma": "Interface language",
        "estado": "Service status",
        "estado_ok": "API available",
        "estado_cargando": "The API responds, but the model is still loading",
        "estado_caido": "The API is not responding",
        "estado_ok_nube": "Model available",
        "estado_cargando_nube": (
            "Loading the model. The first visit takes a few minutes; then press Analyze again."
        ),
        "estado_sin_modelo": "The model could not be loaded. Please notify the project team.",
        "inferencia_nube": "cloud demo",
        "privacidad_nube": (
            "Public demo hosted on Streamlit Community Cloud (servers in the United States). The email is analyzed "
            "in memory and not stored, but do not paste real emails with personal data: use the examples or "
            "test emails."
        ),
        "error_limite": "You reached the limit of {n} analyses for this demo session.",
        "privacidad": (
            "The email is sent only to the detector API, which does not store it. The history exists only in "
            "this browser session and is deleted when it ends."
        ),
        "pestana_analizar": "Analyze",
        "pestana_historial": "History",
        "pestana_acerca": "About the model",
        "pestana_ayuda": "Help",
        "ejemplo": "Example email",
        "boton_ejemplo": "Try an example",
        "modo_texto": "Paste the text",
        "modo_eml": "Upload an .eml file",
        "asunto": "Subject",
        "cuerpo": "Email body",
        "ayuda_cuerpo": "Plain text or HTML. URLs may be defanged (hxxps[://]...).",
        "archivo": ".eml file (up to 1.5 MB)",
        "prioridad_eml": "If you upload a file, the file is analyzed instead of the pasted text.",
        "caracteres": "characters",
        "boton_analizar": "Analyze",
        "boton_limpiar": "Clear",
        "procesando": "Analyzing the email...",
        "error_vacio": "Enter the subject or the body of the email, or upload an .eml file.",
        "error_asunto_largo": "The subject exceeds 1,000 characters.",
        "error_cuerpo_largo": "The body exceeds 500,000 characters.",
        "error_eml_grande": "The file exceeds 1.5 MB.",
        "error_sin_conexion": (
            "Could not connect to the detector API. Check that the service is running (docker compose up -d) "
            "and that G17_API_URL points to it."
        ),
        "error_tiempo_agotado": "The API took too long to respond. Try again in a few seconds.",
        "error_clave_invalida": "The API rejected the key. Check the G17_API_KEY variable of the interface.",
        "error_modelo_no_disponible": "The model is still loading (the first time may take a few minutes). Try again.",
        "error_entrada_invalida": "The API rejected the content. Check that the file is a valid .eml.",
        "error_error_servidor": "The API had an internal error. The analysis was not completed.",
        "error_respuesta_invalida": "The API returned a response that does not follow the contract.",
        "aviso_corto": (
            "The text has fewer than {n} characters. In the evaluation, the detector caught 93% of short phishing "
            "emails versus 96% overall: review the result carefully."
        ),
        "aviso_idioma": (
            "Unsupported language ({idioma}): the model is trained only for English and Spanish. The result is "
            "not reliable and the email must be reviewed manually."
        ),
        "resultado": "Result",
        "clase": "Class",
        "riesgo": "Risk",
        "nivel": "Level",
        "probabilidades": "Probability of each class",
        "ramas": "Model branch details",
        "rama": "Branch",
        "rama_bert": "Text, DistilBERT",
        "rama_base": "Text, TF-IDF",
        "rama_url": "URL (highest score)",
        "sin_url": "The email has no URLs; the URL branch uses a neutral value.",
        "no_aplica": "Not used in this route",
        "iocs": "Indicators found (defanged)",
        "sin_iocs": "No URLs or IP addresses were found.",
        "mitre": "MITRE ATT&CK techniques",
        "ruta": "Model route",
        "idioma_detectado": "Detected language",
        "latencia": "Analysis time",
        "umbral": "Phishing threshold",
        "recomendacion": "What to do",
        "rec_phishing": (
            "Do not open links or attachments and do not reply. Report the email to the security team through "
            "your organization's reporting channel."
        ),
        "rec_spam": "Unwanted email. You can delete it or mark it as spam.",
        "rec_legitimo": (
            "No phishing signals were found. The final decision belongs to the person; if in doubt, confirm with "
            "the sender through another channel."
        ),
        "rec_revision": "This result requires manual review by an analyst.",
        "descargar_json": "Download the result (JSON)",
        "historial_vacio": "There are no analyses in this session yet.",
        "descargar_csv": "Download the history (CSV)",
        "limpiar_historial": "Clear the history",
        "comparacion": "Comparison of the session analyses",
        "metrica": "Metric",
        "valor": "Value",
        "hora": "Time",
        "nombres_clase": {"legitimo": "Legitimate", "spam": "Spam", "phishing": "Phishing"},
        "nombres_nivel": {"bajo": "Low", "medio": "Medium", "alto": "High", "critico": "Critical"},
        "acerca": """
### How it works

The detector combines three branches through late fusion:

1. **DistilBERT** fine-tuned on 38,278 English emails reads the full text (up to 256 tokens).
2. **TF-IDF with logistic regression** over words and characters, an interpretable baseline.
3. **XGBoost over the shape of each URL** (length, symbols, sensitive words, top-level domain),
   computed without visiting the link.

A calibrated meta-classifier combines the three outputs into a probability per class; the risk is 100
times the phishing probability. Spanish emails use a multilingual DistilBERT. Any other language is
flagged for manual review.

### Measured performance
""",
        "tabla_metricas": {
            "Macro F1 (test, 8,203 English emails)": "{f1_macro:.4f}",
            "Phishing recall (test)": "{recall_phishing:.1%}",
            "Phishing precision (test)": "{precision_phishing:.1%}",
            "Phishing false positive rate (test)": "{fpr_phishing:.2%}",
            "False positives on real corporate email (Enron)": "{fpr_enron_pct}%",
            "Phishing recall on native Spanish": "{recall_espanol:.1%}",
            "False positives on native Spanish": "{fpr_espanol:.1%}",
            "End-to-end latency (95th percentile)": "{latencia_p95_ms} ms",
        },
        "limitaciones": """
### Limitations and warnings

* **Support, not a decision.** The result guides the analyst; it must not block or delete emails
  without human review.
* **Short emails or emails without URLs.** Recall drops to 93% for texts under 300 characters and to
  94% for emails without URLs.
* **New campaigns.** With a phishing source never seen before, recall dropped to 84% in the
  evaluation. The model needs periodic retraining.
* **Spanish.** False positives (3.5%) exceed the 2% target; Spanish positives must be confirmed.
* **Other languages.** Not supported: the result is not reliable.
* **Training data.** Public English corpora from 1998 to 2026, plus SpaPhish and SpearPhishMX in
  Spanish; they do not represent the email of any specific organization.

### Acceptable use

The tool is meant for security teams and users who report suspicious emails. It must not be used to
analyze other people's email without authorization or to test variations of a phishing email until
it evades detection. Indicators are always shown defanged and the tool never visits links.
""",
        "ayuda": """
### Step by step

1. Paste the subject and body of the email, or upload the .eml file (in most email clients:
   *Download message* or *Save as*).
2. Press **Analyze**. The result appears in one or two seconds.
3. Review the class, the risk and the indicators. The recommendation says what to do.
4. Download the result as JSON or the session history as CSV if you need to attach it to a report.

To try it without an email of your own, choose an example and press **Try an example**.

### Troubleshooting

| Message | Cause | Solution |
|---|---|---|
| Could not connect to the API | The service is not running | `docker compose up -d` in the `deploy` folder |
| The model is still loading | First model download | Wait 2 to 4 minutes |
| The API rejected the key | Different keys in the API and the interface | Check `API_KEY` in `deploy/.env` |
| Unsupported language | Email in a language other than English or Spanish | Manual review |

### FAQ

**Is the email stored?** No. The API does not store it and the history lives only in this session.

**Are links visited?** No. URLs are analyzed only by their shape.

**What does a risk of 85 mean?** The model estimates a phishing probability of 0.85. The operating
threshold is 0.86: above it, the email is classified as phishing.

**How do I switch between light and dark themes?** In the three-dot menu (top right): *System*, *Light* or
*Dark*. By default the interface follows the operating system preference.

Support: the project repository on GitHub (*Issues* section).
""",
    },
}
