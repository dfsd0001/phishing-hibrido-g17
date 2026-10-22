# Despliegue local

Entorno de demostración del detector integrado con un SOC: API de inferencia, interfaz web, n8n,
DFIR-IRIS y Wazuh, todos en contenedores en el mismo equipo. Ningún servicio se expone a internet: los
puertos se publican solo en `127.0.0.1` y la red `soc` es interna. La demostración pública de la
interfaz, sin la integración con el SOC, se describe en `nube/README.md`.

| Servicio | Versión | Dirección local | Función |
|---|---|---|---|
| `api` | Imagen propia `g17/phishing-api:1.1` | `http://127.0.0.1:8000` | Inferencia (contrato JSON v1.2) |
| `ui` | Imagen propia `g17/phishing-ui:1.0` | `http://127.0.0.1:8501` | Interfaz web |
| `n8n` | 2.41.6 | `http://127.0.0.1:5678` | Flujo de triaje: API, DFIR-IRIS y Wazuh |
| `wazuh` | Manager 4.14.8 (sin indexador ni panel) | Solo red interna | Reglas 100500 a 100503 y `alerts.json` |
| DFIR-IRIS | 2.4.29 (compose oficial) | `https://localhost` | Gestor de casos y alertas |

Memoria aproximada: DFIR-IRIS 2,5 GB, API hasta 3 GB, Wazuh hasta 2 GB, n8n hasta 1 GB e interfaz hasta
512 MB. En Windows con Docker Desktop y WSL2, asigne al menos 12 GB en `%UserProfile%\.wslconfig`:

```
[wsl2]
memory=12GB
```

y reinicie WSL con `wsl --shutdown`.

## Archivos

```
deploy/
├── docker-compose.yml     Servicios api, ui, n8n y wazuh (las imágenes propias se construyen desde la raíz)
├── .env.example           Plantilla de variables; se copia a .env, que nunca se versiona
├── n8n/
│   ├── g17_flujo_triaje.json   Flujo exportado para importar en n8n
│   ├── generar_flujo.py        Genera el flujo a partir de los nodos de código de codigo/
│   └── codigo/                 Mapeo del contrato a IRIS y Wazuh, y manejo de fallos de la API
├── wazuh/
│   ├── g17_rules.xml           Reglas 100500 a 100503 (técnica T1566)
│   └── evento_prueba.json      Evento de ejemplo para wazuh-logtest
└── pruebas/
    ├── lote_kpi.py             KPI de alertas integradas
    ├── triaje_cronometro.py    KPI de tiempo de triaje
    └── simuladores.py          API, IRIS y Wazuh simulados para las pruebas automáticas del flujo
```

## Requisitos

* Docker Engine o Docker Desktop con Docker Compose v2.
* Un token de **solo lectura** de Hugging Face con acceso al repositorio privado de modelos (ver
  `models/README.md`).
* Git, para descargar DFIR-IRIS.

## A. DFIR-IRIS

DFIR-IRIS va primero porque su compose crea la red `iris_frontend`, que usa n8n.

```bash
git clone --depth 1 --branch v2.4.29 https://github.com/dfir-iris/iris-web.git
cd iris-web
cp .env.model .env
```

Genere cinco valores aleatorios:

```bash
docker run --rm python:3.13-slim python -c "import secrets; [print(secrets.token_hex(32)) for _ in range(5)]"
```

En `iris-web/.env`, use cuatro de ellos en `POSTGRES_PASSWORD`, `POSTGRES_ADMIN_PASSWORD`,
`IRIS_SECRET_KEY` e `IRIS_SECURITY_PASSWORD_SALT`. Descomente `IRIS_ADM_PASSWORD` (con una contraseña
robusta) e `IRIS_ADM_API_KEY` (con el quinto valor, que también irá como `IRIS_API_KEY` en
`deploy/.env`). Luego:

```bash
docker compose pull
docker compose up -d
```

La interfaz queda en `https://localhost` con el usuario `administrator` (certificado autofirmado). El
compose oficial publica el puerto 443 en todas las interfaces: en un laboratorio, limítelo con el
firewall del equipo.

## B. API, interfaz, n8n y Wazuh

Desde la carpeta `deploy/` de este repositorio:

```bash
cp .env.example .env
```

Complete `.env`:

| Variable | Valor |
|---|---|
| `API_KEY` | Una clave aleatoria; la usan n8n y la interfaz para llamar a la API |
| `HF_TOKEN` | Token de solo lectura de Hugging Face |
| `MODEL_REPO`, `MODEL_REVISION` | `dennysSalazar/g17-phishing-hibrido` y `v2` (ya completados) |
| `UMBRAL_EN` | `0.8586`, umbral operativo de la ruta inglesa (ya completado) |
| `DOMINIOS_PROPIOS` | Opcional: dominios de la organización separados por coma |
| `IRIS_API_KEY` | El mismo valor que `IRIS_ADM_API_KEY` de `iris-web/.env` |
| `WAZUH_API_PASSWORD` | Entre 8 y 64 caracteres, con mayúscula, minúscula, número y uno de `. * + ? -` |

Levante el entorno:

```bash
docker compose up -d --build
docker compose ps
```

La primera vez la API descarga el modelo (de 2 a 5 minutos) y la interfaz arranca cuando la API está
*healthy*. Para levantar solo la API y la interfaz, sin el SOC: `docker compose up -d --build api ui`.

## C. Pruebas de conectividad

```bash
docker compose exec api python /app/api/scripts/prueba_api.py
docker compose exec n8n node -e "fetch('http://api:7860/salud').then(r=>r.json()).then(j=>console.log('n8n->api', j.estado))"
docker compose exec n8n node -e "fetch('http://app:8000/login').then(r=>console.log('n8n->iris HTTP', r.status))"
docker compose exec -T wazuh /var/ossec/bin/wazuh-logtest < wazuh/evento_prueba.json
```

Resultado esperado: la prueba de la API clasifica el correo de credenciales como phishing por la ruta
`en_v3` y el correo en español por la ruta `es_v1` sin advertencias; n8n alcanza la API (`ok`) e IRIS
(HTTP 200); `wazuh-logtest` dispara la regla 100502. Nunca pegue claves en reportes ni en *issues*.

## D. Flujo de n8n

1. Abra `http://localhost:5678` y cree el usuario propietario.
2. *Workflows*, *Import from File*, elija `n8n/g17_flujo_triaje.json`. No necesita credenciales: las
   claves se leen de las variables de entorno del contenedor.
3. Active el flujo (*Publish*). El webhook queda en `http://127.0.0.1:5678/webhook/g17-correo`.

El modelo sugiere y el analista decide: el flujo nunca cierra un caso por su cuenta.

| Caso | Alerta en DFIR-IRIS | Evento en Wazuh |
|---|---|---|
| Clase phishing | Sí, severidad *Critical* (nivel crítico) o *High* | Regla 100501 o 100502 |
| Idioma no soportado | Sí, severidad *Medium*, etiqueta `revision_manual` | Regla 100503 |
| Spam o legítimo | No | Regla 100500 |
| La API falla | Sí, severidad *Medium*, `fallo_api` (cola manual, nunca cierre) | Regla 100500 |
| Respuesta con un indicador vivo | Se bloquea: el flujo falla a propósito | No |

Prueba rápida:

```bash
curl -s -X POST http://127.0.0.1:5678/webhook/g17-correo \
  -H "Content-Type: application/json" \
  -d '{"asunto":"Account suspended","cuerpo":"Your mailbox will be deleted. Verify your password at https://secure-login.example.com/verify within 24 hours."}'
```

Resultado esperado: `iris.estado` igual a `creada`, con `alerta_id`, y `wazuh.estado` igual a
`enviado`. En Wazuh:

```bash
docker compose exec wazuh grep -c "10050" /var/ossec/logs/alerts/alerts.json
```

## E. KPI de alertas integradas (meta: más de 90 %)

1. Genere la muestra de 200 correos de prueba con `notebooks/experimentos/14_muestra_kpi.ipynb` y
   copie `kpi_muestra.csv` a `deploy/pruebas/`.
2. Ejecute, con la clave de IRIS en la variable de entorno:

   ```bash
   cd deploy/pruebas
   export IRIS_API_KEY=<clave>
   python lote_kpi.py kpi_muestra.csv
   ```

   El lote tarda unos 7 minutos, porque respeta el límite de 30 eventos por minuto de la API de Wazuh.
3. El resultado queda en `kpi_resumen.json` y `kpi_resultados.csv`, sin claves ni texto de correos. Los
   del 14/10/2026 están en `results/metrics/kpi/`.

## F. KPI de tiempo de triaje (meta: reducción de 40 % o más)

Diseño cruzado: 20 correos en dos bloques, dos analistas; cada correo se clasifica una vez de forma
manual y una vez con la sugerencia del modelo, por personas distintas.

```bash
export API_KEY=<clave de la API>
python triaje_cronometro.py preparar kpi_muestra.csv
python triaje_cronometro.py sesion --analista 1
python triaje_cronometro.py sesion --analista 2
python triaje_cronometro.py resumen
```

El resultado (`triaje_resumen.json`) es una estimación por el tamaño de la muestra y así se reporta.

## Detener y limpiar

```bash
docker compose down          # detiene los servicios y conserva los volúmenes
docker compose down -v       # además borra el modelo descargado, los datos de n8n y los registros de Wazuh
```
