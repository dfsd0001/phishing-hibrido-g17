# Demostración pública en Streamlit Community Cloud

La interfaz del detector se publica en **https://phishing-hibrido-g17.streamlit.app** para que se
pueda probar desde cualquier navegador, sin instalar nada. Es la misma interfaz de `app/` y el mismo
detector publicado (versión `v2`), con dos diferencias frente al despliegue local:

| | Despliegue local (`deploy/`) | Demostración en la nube (`nube/`) |
|---|---|---|
| Dónde corre el modelo | En la API, un contenedor aparte | Dentro de la propia interfaz (modo `local`) |
| Integración con el SOC | n8n, DFIR-IRIS y Wazuh | No incluida |
| Correos que se pueden analizar | Los de la organización, sin salir de su red | Solo ejemplos o correos de prueba: los servidores están en Estados Unidos |
| Límite de uso | Ninguno | 30 análisis por sesión |

En los dos casos la salida sigue el contrato JSON v1.2 y se valida contra su esquema, los indicadores
salen defangeados y ninguna URL se resuelve ni se visita.

## Por qué Streamlit Community Cloud

| Plataforma | Plan gratuito (verificado en octubre de 2026) | Resultado |
|---|---|---|
| Hugging Face Spaces | Desde julio de 2026, los Spaces de Gradio y Docker en CPU gratuita exigen una suscripción PRO (el proyecto recibió el error 402 al crear uno, decisión D12) | No disponible |
| Render | 0,1 CPU y 512 MB de RAM | Insuficiente: PyTorch y un DistilBERT superan esa memoria |
| Streamlit Community Cloud | Hasta 2 núcleos y 2,7 GB de RAM; la aplicación se suspende tras 12 horas sin visitas | Suficiente para los dos DistilBERT en CPU |

## Archivos

| Archivo | Función |
|---|---|
| `streamlit_app.py` | Punto de entrada: activa el modo `local`, el umbral operativo y el límite por sesión, y ejecuta `app/app.py` |
| `requirements.txt` | Dependencias mínimas de inferencia e interfaz; PyTorch en su variante para CPU |
| `../.streamlit/config.toml` | Tema claro y oscuro (la plataforma solo lee la configuración de la raíz) |
| `../app/motor_local.py` | Carga el detector desde Hugging Face Hub en un hilo aparte y valida cada salida contra el contrato |

## Publicar o volver a publicar

**1. Token de Hugging Face.** El repositorio de modelos es privado. En
`huggingface.co/settings/tokens`, cree un token *Fine-grained* con un único permiso: lectura del
contenido de `dennysSalazar/g17-phishing-hibrido`. Ese token solo puede leer ese repositorio y se puede
revocar en cualquier momento.

**2. Crear la aplicación.** En `share.streamlit.io`, inicie sesión con la cuenta de GitHub dueña del
repositorio y elija *Create app*, *Deploy a public app from GitHub*:

| Campo | Valor |
|---|---|
| Repository | `dfsd0001/phishing-hibrido-g17` |
| Branch | `main` |
| Main file path | `nube/streamlit_app.py` |
| App URL | `phishing-hibrido-g17` |

**3. Configuración avanzada** (*Advanced settings*): Python 3.13 y, en *Secrets*:

```toml
HF_TOKEN = "<token del paso 1>"
UMBRAL_EN = "0.8586"
```

Los secretos nunca se escriben en el repositorio. La plataforma los entrega a la aplicación como
variables de entorno.

**4. Desplegar.** La primera vez la plataforma instala las dependencias (varios minutos) y, al abrir
la página, la aplicación descarga los artefactos del modelo y los precalienta (de 1 a 3 minutos).
Mientras tanto la barra lateral muestra *Cargando el modelo*. Cuando cambia a *Modelo disponible*, la
aplicación está lista.

## Operación

* **Suspensión.** Tras 12 horas sin visitas la aplicación se suspende. Cualquier visitante la despierta
  con el botón *Yes, get this app back up!*; después hay que esperar de nuevo la carga del modelo.
  Antes de una evaluación conviene abrirla unos minutos antes.
* **Actualizaciones.** Cada cambio en la rama `main` se vuelve a desplegar solo.
* **Registros.** En *Manage app* se ven la instalación y los errores. Si la aplicación supera la
  memoria disponible, se reinicia y el registro lo indica.

## Seguridad y uso responsable

La guía del proyecto recomendaba no publicar el detector en internet: una instancia pública puede
servir para probar un correo de phishing una y otra vez hasta que el detector no lo marque
(`docs/consideraciones_eticas.md`, sección 7). La demostración se publica porque la evaluación del
proyecto exige una URL pública, y se limita así:

* los pesos del modelo siguen privados; la aplicación los lee con un token de solo lectura guardado
  como secreto de la plataforma;
* hay un máximo de 30 análisis por sesión;
* la barra lateral advierte que no se peguen correos reales con datos personales;
* la integración con el SOC no se publica.

El límite por sesión es una fricción, no una barrera: basta con recargar la página para empezar otra
sesión. Terminada la evaluación del proyecto, la aplicación se puede suspender o borrar desde el panel
de la plataforma.

## Fuentes

* Streamlit, límites de recursos y suspensión de Community Cloud:
  https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
* Streamlit, secretos como variables de entorno:
  https://docs.streamlit.io/develop/concepts/connections/secrets-management
* Render, planes de cómputo: https://render.com/docs/compute-plans
* Foro de Hugging Face, cambio en los Spaces gratuitos de CPU (julio de 2026):
  https://discuss.huggingface.co/t/official-community-complaint-revert-free-cpu-basic-spaces-and-remove-anti-developer-sdk-restrictions/177703
