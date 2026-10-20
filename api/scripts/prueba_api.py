"""Prueba de humo del servicio desde dentro del contenedor.

Uso:
    docker compose exec api python /app/api/scripts/prueba_api.py

Los correos de ejemplo usan dominios reservados para documentación (RFC 2606) y se guardan
defangeados; se refangan solo en memoria antes de enviarlos. El script no imprime la clave.
"""

import json
import os
import time
import urllib.request

URL_SERVICIO = "http://localhost:7860"

CASOS = [
    (
        "Account suspended",
        "Dear user, your mailbox will be deleted. Verify your password at "
        "hxxps[://]secure-login[.]example[.]com/verify?id=7 within 24 hours.",
    ),
    (
        "Reunión de equipo",
        "Hola equipo, nos vemos el martes a las diez para revisar el informe trimestral del proyecto.",
    ),
    (
        "Q3 budget review",
        "Hi Maria, please find below the summary of the third quarter budget review. Operating costs "
        "were within the approved range and the procurement team will share the detailed breakdown "
        "next Tuesday during the planning meeting. Regards, Carlos",
    ),
]


def refang(texto: str) -> str:
    return texto.replace("hxxp", "http").replace("[://]", "://").replace("[.]", ".")


def analizar(clave: str, asunto: str, cuerpo: str) -> tuple[dict, int]:
    datos = json.dumps({"asunto": asunto, "cuerpo": refang(cuerpo)}).encode()
    solicitud = urllib.request.Request(
        f"{URL_SERVICIO}/v1/analizar",
        data=datos,
        headers={"Content-Type": "application/json", "X-API-Key": clave},
    )
    inicio = time.time()
    with urllib.request.urlopen(solicitud) as respuesta:
        resultado = json.load(respuesta)
    return resultado, round(1000 * (time.time() - inicio))


def main() -> None:
    clave = os.environ["API_KEY"]
    with urllib.request.urlopen(f"{URL_SERVICIO}/salud") as respuesta:
        print("salud:", json.load(respuesta))
    for asunto, cuerpo in CASOS:
        r, ms = analizar(clave, asunto, cuerpo)
        c = r["clasificacion"]
        print(
            f"{asunto[:20]:20} clase={c['clase']:9} riesgo={c['riesgo']:3} nivel={c['nivel_riesgo']:8} "
            f"idioma={r['idioma_detectado']} ruta={r['ruta_modelo']} urls={r['iocs']['urls']} {ms} ms"
        )


if __name__ == "__main__":
    main()
