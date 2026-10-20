"""Simuladores locales para probar el flujo de n8n sin el despliegue completo.

Levanta tres servicios en 127.0.0.1 con el formato de respuesta real de cada uno:

* API del detector (puerto 7860): devuelve los archivos de referencia del contrato.
* DFIR-IRIS (puerto 8000): ``POST /alerts/add`` y ``GET /alerts/filter``.
* API de Wazuh (puerto 55000, HTTPS): autenticación JWT y ``POST /events`` con el límite de
  30 solicitudes por minuto de la versión 4.14.8.

Palabras clave en el cuerpo del correo para forzar escenarios:
    password       respuesta de phishing
    offer          respuesta de spam
    bonjour        idioma no soportado
    provocar_fallo la API responde 500
    ioc_vivo       la API devuelve una URL sin defangear (el flujo debe bloquearla)

Uso:
    python simuladores.py contracts/golden cert.pem key.pem
"""

import base64
import copy
import json
import ssl
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CLAVE_API = "clave-api-prueba"
CLAVE_IRIS = "clave-iris-prueba"
USUARIO_WAZUH = "wazuh-wui:Prueba.2026"
LIMITE_EVENTOS_POR_MINUTO = 30


class Estado:
    def __init__(self, carpeta_referencias: Path):
        self.referencias = {
            nombre: json.loads((carpeta_referencias / f"{nombre}.json").read_text(encoding="utf-8"))
            for nombre in ("legitimo", "phishing", "spam")
        }
        self.alertas: list[dict] = []
        self.eventos: list[dict] = []
        self.inicios_sesion = 0
        self.ventana_eventos: list[float] = []


class ManejadorBase(BaseHTTPRequestHandler):
    estado: Estado

    def log_message(self, *args):
        pass

    def responder(self, codigo: int, cuerpo: dict) -> None:
        datos = json.dumps(cuerpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def leer_json(self) -> dict:
        longitud = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(longitud) or b"{}")


class ApiDetector(ManejadorBase):
    def do_GET(self):
        self.responder(200, {"estado": "ok"})

    def do_POST(self):
        if self.headers.get("X-API-Key") != CLAVE_API:
            self.responder(401, {"detail": "Clave inválida"})
            return
        cuerpo = self.leer_json()
        texto = (cuerpo.get("asunto", "") + " " + cuerpo.get("cuerpo", "")).lower()
        if "provocar_fallo" in texto:
            self.responder(500, {"detail": "fallo simulado"})
            return
        if "password" in texto or "bonjour" in texto:
            clase = "phishing"
        elif "offer" in texto:
            clase = "spam"
        else:
            clase = "legitimo"
        respuesta = copy.deepcopy(self.estado.referencias[clase])
        respuesta["id_analisis"] = str(uuid.uuid4())
        respuesta["advertencias"] = []
        respuesta["ruta_modelo"] = "en_v3"
        respuesta["idioma_detectado"] = "en"
        if "bonjour" in texto:
            respuesta["idioma_detectado"] = "fr"
            respuesta["advertencias"] = ["idioma_no_soportado"]
        if "ioc_vivo" in texto:
            respuesta["iocs"]["urls"] = ["https://malicioso.example.com/x"]
        self.responder(200, respuesta)


class Iris(ManejadorBase):
    def do_GET(self):
        self.responder(
            200, {"status": "success", "data": {"alerts": self.estado.alertas, "total": len(self.estado.alertas)}}
        )

    def do_POST(self):
        if self.headers.get("Authorization") != f"Bearer {CLAVE_IRIS}":
            self.responder(401, {"status": "error"})
            return
        alerta = self.leer_json()
        alerta["alert_id"] = len(self.estado.alertas) + 1
        self.estado.alertas.append(alerta)
        self.responder(200, {"status": "success", "message": "Alert added", "data": alerta})


class Wazuh(ManejadorBase):
    def do_GET(self):
        self.responder(200, {"eventos": self.estado.eventos, "inicios_sesion": self.estado.inicios_sesion})

    def do_POST(self):
        if self.path.startswith("/security/user/authenticate"):
            esperado = "Basic " + base64.b64encode(USUARIO_WAZUH.encode()).decode()
            if self.headers.get("Authorization") != esperado:
                self.responder(401, {"title": "Unauthorized"})
                return
            self.estado.inicios_sesion += 1
            self.responder(200, {"data": {"token": "jwt-prueba"}, "error": 0})
            return
        if self.path != "/events":
            self.responder(404, {})
            return
        if self.headers.get("Authorization") != "Bearer jwt-prueba":
            self.responder(401, {})
            return
        ahora = time.time()
        self.estado.ventana_eventos = [t for t in self.estado.ventana_eventos if ahora - t < 60]
        if len(self.estado.ventana_eventos) >= LIMITE_EVENTOS_POR_MINUTO:
            self.responder(429, {"title": "Too Many Requests"})
            return
        self.estado.ventana_eventos.append(ahora)
        eventos = self.leer_json()["events"]
        self.estado.eventos.extend(json.loads(e) for e in eventos)
        self.responder(200, {"data": {"affected_items": [], "total_affected_items": len(eventos)}, "error": 0})


def arrancar(manejador, estado: Estado, puerto: int, tls: tuple[str, str] | None = None) -> None:
    clase = type(manejador.__name__, (manejador,), {"estado": estado})
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), clase)
    if tls:
        contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto.load_cert_chain(*tls)
        servidor.socket = contexto.wrap_socket(servidor.socket, server_side=True)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()


def main() -> None:
    carpeta, certificado, clave = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    estado = Estado(carpeta)
    arrancar(ApiDetector, estado, 7860)
    arrancar(Iris, estado, 8000)
    arrancar(Wazuh, estado, 55000, tls=(certificado, clave))
    print("Simuladores listos: API 7860, IRIS 8000, Wazuh 55000", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
