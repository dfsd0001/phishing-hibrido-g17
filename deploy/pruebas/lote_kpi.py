"""Medición del KPI de alertas integradas sobre el despliegue local.

Envía la muestra de prueba (``kpi_muestra.csv``, generada por
``notebooks/experimentos/14_muestra_kpi.ipynb``) al webhook de n8n y mide:

* Alertas integradas: alertas creadas en DFIR-IRIS sobre correos clasificados como phishing.
* Eventos entregados a Wazuh sobre correos enviados.
* Latencia de extremo a extremo (webhook, API, IRIS y Wazuh), percentiles 50 y 95.
* Matriz etiqueta real frente a clase sugerida, como control de coherencia.
* Verificación cruzada: total de alertas del detector en IRIS antes y después del lote.

Seguridad: el CSV guarda el texto defangeado. El refang ocurre solo en memoria, dentro del
cuerpo de la solicitud al webhook local; no se escribe texto refangeado a disco.

Uso (Python 3.10 o superior, sin dependencias externas):
    python lote_kpi.py kpi_muestra.csv

Variables de entorno: ``N8N_WEBHOOK``, ``IRIS_HOST``, ``IRIS_API_KEY`` y ``PAUSA_S``.
Salidas: ``kpi_resultados.csv`` y ``kpi_resumen.json``, sin claves ni texto de correos.
"""

import csv
import json
import os
import re
import ssl
import statistics
import sys
import time
import urllib.error
import urllib.request

# Los correos en HTML pueden superar el límite por defecto de 128 KB por campo.
csv.field_size_limit(2**31 - 1)

WEBHOOK = os.getenv("N8N_WEBHOOK", "http://127.0.0.1:5678/webhook/g17-correo")
IRIS = os.getenv("IRIS_HOST", "https://localhost")
IRIS_API_KEY = os.getenv("IRIS_API_KEY", "")
# Wazuh 4.14.8 acepta 30 solicitudes por minuto en POST /events: un correo cada 2,1 s.
PAUSA_S = float(os.getenv("PAUSA_S", "2.1"))
FUENTE_ALERTAS = "G17-detector-phishing"


def _contexto_tls() -> ssl.SSLContext:
    """IRIS usa un certificado autofirmado en el laboratorio: no se verifica la cadena."""
    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE
    return contexto


def refang_en_memoria(texto: str) -> str:
    texto = re.sub(r"(?i)hxxp", "http", texto)
    return texto.replace("[://]", "://").replace("[:]", ":").replace("[.]", ".").replace("[@]", "@")


def enviar(url: str, cuerpo: dict, tiempo_maximo: int = 120) -> tuple[int, dict]:
    solicitud = urllib.request.Request(
        url, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(solicitud, timeout=tiempo_maximo) as respuesta:
        return respuesta.status, json.load(respuesta)


def total_alertas_iris() -> int | None:
    """Número de alertas del detector registradas en IRIS, o ``None`` si no se puede consultar."""
    if not IRIS_API_KEY:
        return None
    url = f"{IRIS}/alerts/filter?per_page=1&page=1&alert_source={FUENTE_ALERTAS}"
    solicitud = urllib.request.Request(url, headers={"Authorization": f"Bearer {IRIS_API_KEY}"})
    contexto = _contexto_tls() if url.startswith("https") else None
    try:
        with urllib.request.urlopen(solicitud, context=contexto, timeout=30) as respuesta:
            return int(json.load(respuesta)["data"]["total"])
    except (urllib.error.URLError, KeyError, ValueError) as error:
        print(f"  No se pudo consultar IRIS: {error}")
        return None


def porcentaje(parte: int, total: int) -> float | None:
    return round(100 * parte / total, 1) if total else None


def procesar_correo(fila: dict) -> dict:
    inicio = time.time()
    try:
        estado, respuesta = enviar(WEBHOOK, {"asunto": "", "cuerpo": refang_en_memoria(fila["texto_defang"])})
    except urllib.error.HTTPError as error:
        estado, respuesta = error.code, {"error": str(error)[:120]}
    except (urllib.error.URLError, TimeoutError) as error:
        estado, respuesta = 0, {"error": str(error)[:120]}
    milisegundos = round(1000 * (time.time() - inicio))
    time.sleep(max(0.0, PAUSA_S - milisegundos / 1000))
    iris = respuesta.get("iris") or {}
    return {
        "id": fila["id"],
        "idioma": fila["idioma"],
        "etiqueta": fila["clase"],
        "http": estado,
        "clase": respuesta.get("clase"),
        "riesgo": respuesta.get("riesgo"),
        "ruta_modelo": respuesta.get("ruta_modelo"),
        "advertencias": ";".join(respuesta.get("advertencias") or []),
        "iris_requerida": iris.get("requerida"),
        "iris_estado": iris.get("estado"),
        "iris_alerta_id": iris.get("alerta_id"),
        "wazuh_estado": (respuesta.get("wazuh") or {}).get("estado"),
        "ms_extremo_a_extremo": milisegundos,
        "error": respuesta.get("error", respuesta.get("message", "")),
    }


def resumir(resultados: list[dict], iris_antes: int | None, iris_despues: int | None) -> dict:
    correctos = [r for r in resultados if r["http"] == 200]
    phishing = [r for r in correctos if r["clase"] == "phishing"]
    requeridas = [r for r in correctos if r["iris_requerida"]]
    latencias = sorted(r["ms_extremo_a_extremo"] for r in correctos)
    matriz: dict[str, int] = {}
    for r in correctos:
        clave = f"{r['idioma']}|{r['etiqueta']}->{r['clase']}"
        matriz[clave] = matriz.get(clave, 0) + 1
    estados_wazuh = sorted({str(r["wazuh_estado"]) for r in correctos})
    return {
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_enviados": len(resultados),
        "n_http_200": len(correctos),
        "n_errores": len(resultados) - len(correctos),
        "kpi_alertas_integradas_pct": porcentaje(sum(r["iris_estado"] == "creada" for r in phishing), len(phishing)),
        "n_clasificados_phishing": len(phishing),
        "alertas_iris_requeridas": len(requeridas),
        "alertas_iris_creadas": sum(r["iris_estado"] == "creada" for r in requeridas),
        "eventos_wazuh_enviados_pct": porcentaje(
            sum(r["wazuh_estado"] == "enviado" for r in correctos), len(correctos)
        ),
        "wazuh_estados": {e: sum(str(r["wazuh_estado"]) == e for r in correctos) for e in estados_wazuh},
        "latencia_ms_p50": statistics.median(latencias) if latencias else None,
        "latencia_ms_p95": latencias[max(0, round(0.95 * len(latencias)) - 1)] if latencias else None,
        "iris_alertas_antes": iris_antes,
        "iris_alertas_despues": iris_despues,
        "iris_delta": None if iris_antes is None or iris_despues is None else iris_despues - iris_antes,
        "matriz_etiqueta_vs_sugerida": dict(sorted(matriz.items())),
        "meta": "alertas integradas > 90 % (Matriz de KPIs)",
    }


def main(ruta: str) -> int:
    with open(ruta, encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    minutos = round(len(filas) * (PAUSA_S + 0.4) / 60)
    print(f"Muestra: {len(filas)} correos, webhook {WEBHOOK}, pausa {PAUSA_S} s (unos {minutos} min)")
    iris_antes = total_alertas_iris()
    resultados = []
    for i, fila in enumerate(filas, 1):
        resultados.append(procesar_correo(fila))
        if i % 20 == 0:
            print(f"  {i}/{len(filas)}")
    resumen = resumir(resultados, iris_antes, total_alertas_iris())

    with open("kpi_resultados.csv", "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(resultados[0].keys()))
        escritor.writeheader()
        escritor.writerows(resultados)
    with open("kpi_resumen.json", "w", encoding="utf-8") as archivo:
        json.dump(resumen, archivo, ensure_ascii=False, indent=1)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "kpi_muestra.csv"))
