"""Genera el flujo de n8n ``g17_flujo_triaje.json`` a partir del código de ``codigo/*.js``.

Flujo: Webhook -> API del detector -> (si corresponde) alerta en DFIR-IRIS -> evento en Wazuh
-> respuesta. Las claves no se incluyen en el flujo: los nodos las leen de las variables de
entorno del contenedor de n8n (``G17_API_KEY``, ``IRIS_API_KEY``, ``WAZUH_API_USER`` y
``WAZUH_API_PASSWORD``).

Uso (desde la raíz del repositorio):
    python deploy/n8n/generar_flujo.py
"""

import json
import uuid
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
NOMBRE = "G17 - Triaje de correo reportado (API, IRIS y Wazuh) v1.3"
# La importación por línea de comandos exige un identificador; la importación desde la interfaz lo reemplaza.
ID_FLUJO = "g17TriajeCorreo1"
ESPACIO_UUID = uuid.UUID("6f1c2b9e-7a43-4c1e-9b1d-0c17a0a17001")

WEBHOOK = "Correo reportado"
API = "Analizar (API G17)"
MAPEAR = "Mapear contrato a IRIS y Wazuh"
FALLO = "Fallo API: revisión manual"
DECIDIR = "¿Requiere alerta IRIS?"
IRIS = "Crear alerta IRIS"
WAZUH = "Evento a Wazuh"
RESPONDER = "Responder"


def _id(nombre: str) -> str:
    """Identificador estable por nodo, para que regenerar el flujo no produzca cambios espurios."""
    return str(uuid.uuid5(ESPACIO_UUID, nombre))


def _codigo(archivo: str) -> str:
    return (CARPETA / "codigo" / archivo).read_text(encoding="utf-8").strip()


def _nodo(nombre: str, tipo: str, version: float, posicion: list[int], parametros: dict, **extra) -> dict:
    return {
        "id": _id(nombre),
        "name": nombre,
        "type": f"n8n-nodes-base.{tipo}",
        "typeVersion": version,
        "position": posicion,
        "parameters": parametros,
        **extra,
    }


def _nodo_codigo(nombre: str, archivo: str, posicion: list[int]) -> dict:
    return _nodo(nombre, "code", 2, posicion, {"mode": "runOnceForEachItem", "jsCode": _codigo(archivo)})


def _enlace(destino: str) -> dict:
    return {"node": destino, "type": "main", "index": 0}


def construir() -> dict:
    nodos = [
        _nodo(
            WEBHOOK,
            "webhook",
            2,
            [0, 300],
            {"httpMethod": "POST", "path": "g17-correo", "responseMode": "responseNode", "options": {}},
            webhookId=_id("webhook"),
        ),
        _nodo(
            API,
            "httpRequest",
            4.2,
            [240, 300],
            {
                "method": "POST",
                "url": "={{ ($env.G17_API_URL || 'http://api:7860') + '/v1/analizar' }}",
                "sendHeaders": True,
                "headerParameters": {"parameters": [{"name": "X-API-Key", "value": "={{ $env.G17_API_KEY }}"}]},
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": (
                    "={{ JSON.stringify({ asunto: $json.body.asunto || '', cuerpo: $json.body.cuerpo || '' }) }}"
                ),
                "options": {"timeout": 30000},
            },
            onError="continueErrorOutput",
        ),
        _nodo_codigo(MAPEAR, "mapear_contrato.js", [500, 200]),
        _nodo_codigo(FALLO, "fallo_api.js", [500, 420]),
        _nodo(
            DECIDIR,
            "if",
            2.2,
            [760, 300],
            {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": _id("condicion-requiere-iris"),
                            "leftValue": "={{ $json.requiere_iris }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        ),
        _nodo(
            IRIS,
            "httpRequest",
            4.2,
            [1000, 200],
            {
                "method": "POST",
                "url": "={{ ($env.IRIS_URL || 'http://app:8000') + '/alerts/add' }}",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [{"name": "Authorization", "value": "={{ 'Bearer ' + $env.IRIS_API_KEY }}"}]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json.iris_payload) }}",
                "options": {"timeout": 30000, "allowUnauthorizedCerts": True},
            },
            onError="continueRegularOutput",
        ),
        _nodo_codigo(WAZUH, "evento_wazuh.js", [1240, 300]),
        _nodo(
            RESPONDER,
            "respondToWebhook",
            1.1,
            [1480, 300],
            {"respondWith": "json", "responseBody": "={{ JSON.stringify($json) }}", "options": {}},
        ),
    ]
    conexiones = {
        WEBHOOK: {"main": [[_enlace(API)]]},
        API: {"main": [[_enlace(MAPEAR)], [_enlace(FALLO)]]},
        MAPEAR: {"main": [[_enlace(DECIDIR)]]},
        FALLO: {"main": [[_enlace(DECIDIR)]]},
        DECIDIR: {"main": [[_enlace(IRIS)], [_enlace(WAZUH)]]},
        IRIS: {"main": [[_enlace(WAZUH)]]},
        WAZUH: {"main": [[_enlace(RESPONDER)]]},
    }
    return {
        "id": ID_FLUJO,
        "name": NOMBRE,
        "nodes": nodos,
        "connections": conexiones,
        "active": False,
        "settings": {"executionOrder": "v1", "timezone": "America/Guayaquil"},
        "pinData": {},
        "meta": {"templateCredsSetupCompleted": True},
        "tags": [],
    }


def main() -> None:
    destino = CARPETA / "g17_flujo_triaje.json"
    destino.write_text(json.dumps(construir(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Flujo generado en {destino}")


if __name__ == "__main__":
    main()
