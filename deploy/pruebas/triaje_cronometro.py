"""Cronometraje del triaje de nivel 1: manual frente a asistido por el detector.

Diseño cruzado para controlar la dificultad de cada correo:

* 20 correos de prueba en dos bloques, A y B (10 y 10), con las tres clases en cada bloque.
* Analista 1: bloque A manual y bloque B asistido. Analista 2: bloque A asistido y bloque B
  manual. Cada correo se clasifica una vez en cada condición, por personas distintas.
* Ambos analistas empiezan por su bloque manual.

El tiempo va desde que se muestra el correo hasta que se registra la decisión. En la condición
asistida se muestra además la sugerencia del modelo (clase, riesgo e IOC defangeados). Todo el
texto se muestra defangeado.

Pasos (Python 3.10 o superior, sin dependencias externas):
    python triaje_cronometro.py preparar kpi_muestra.csv     # requiere API_KEY; llama a la API una vez
    python triaje_cronometro.py sesion --analista 1
    python triaje_cronometro.py sesion --analista 2
    python triaje_cronometro.py resumen

El resultado es una estimación: 20 correos y dos personas. Se reporta con intervalo bootstrap.
"""

import argparse
import csv
import json
import os
import random
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path

csv.field_size_limit(2**31 - 1)

API = os.getenv("G17_API", "http://127.0.0.1:8000")
SEMILLA = 17
OPCIONES = {"l": "legitimo", "s": "spam", "p": "phishing"}
CORREOS_POR_CLASE_Y_BLOQUE = {"phishing": 4, "spam": 3, "legitimo": 3}
MAX_CARACTERES = 2500
MUESTRA = Path("triaje_muestra.json")
REGISTROS = Path("triaje_registros.csv")
COLUMNAS = ["analista", "id", "bloque", "condicion", "clase_real", "decision", "segundos", "sugerencia"]


def refang_en_memoria(texto: str) -> str:
    texto = re.sub(r"(?i)hxxp", "http", texto)
    return texto.replace("[://]", "://").replace("[:]", ":").replace("[.]", ".").replace("[@]", "@")


def condiciones(analista: int) -> dict[str, str]:
    if analista == 1:
        return {"A": "manual", "B": "asistido"}
    return {"A": "asistido", "B": "manual"}


def consultar_api(clave: str, texto_defang: str) -> dict:
    cuerpo = json.dumps({"asunto": "", "cuerpo": refang_en_memoria(texto_defang)}).encode()
    solicitud = urllib.request.Request(
        f"{API}/v1/analizar", data=cuerpo, headers={"Content-Type": "application/json", "X-API-Key": clave}
    )
    with urllib.request.urlopen(solicitud, timeout=120) as respuesta:
        return json.load(respuesta)


def preparar(ruta_csv: str) -> None:
    """Selecciona los 20 correos, obtiene la sugerencia del modelo y guarda la muestra."""
    with open(ruta_csv, encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    generador = random.Random(SEMILLA)
    bloques: dict[str, list[dict]] = {"A": [], "B": []}
    for clase, cantidad in CORREOS_POR_CLASE_Y_BLOQUE.items():
        candidatos = [f for f in filas if f["clase"] == clase and len(f["texto_defang"]) < MAX_CARACTERES]
        generador.shuffle(candidatos)
        bloques["A"] += candidatos[:cantidad]
        bloques["B"] += candidatos[cantidad : 2 * cantidad]

    clave = os.environ["API_KEY"]
    muestra = []
    for bloque, correos in bloques.items():
        generador.shuffle(correos)
        for correo in correos:
            respuesta = consultar_api(clave, correo["texto_defang"])
            clasificacion = respuesta["clasificacion"]
            muestra.append(
                {
                    "id": correo["id"],
                    "bloque": bloque,
                    "idioma": correo["idioma"],
                    "clase_real": correo["clase"],
                    "texto_defang": correo["texto_defang"],
                    "sugerencia": {
                        "clase": clasificacion["clase"],
                        "riesgo": clasificacion["riesgo"],
                        "nivel": clasificacion["nivel_riesgo"],
                        "urls": respuesta["iocs"]["urls"],
                        "ips": respuesta["iocs"]["ips"],
                        "advertencias": respuesta["advertencias"],
                    },
                }
            )
    MUESTRA.write_text(json.dumps(muestra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{MUESTRA}: {len(muestra)} correos (A={len(bloques['A'])}, B={len(bloques['B'])})")


def _mostrar(correo: dict, posicion: int, total: int, condicion: str) -> None:
    print("\n" * 3 + "=" * 90)
    print(f"Correo {posicion}/{total} - condición: {condicion.upper()}")
    print("-" * 90)
    print(correo["texto_defang"][:MAX_CARACTERES])
    if condicion == "asistido":
        s = correo["sugerencia"]
        print("-" * 90)
        print(f"SUGERENCIA DEL MODELO (orientativa): {s['clase']} - riesgo {s['riesgo']}/100 - {s['nivel']}")
        detalle = f"URL: {', '.join(s['urls']) or 'ninguna'} - IP: {', '.join(s['ips']) or 'ninguna'}"
        if s["advertencias"]:
            detalle += f" - advertencias: {s['advertencias']}"
        print(detalle)


def sesion(analista: int) -> None:
    """Muestra los correos al analista y registra decisión y tiempo de cada uno."""
    muestra = json.loads(MUESTRA.read_text(encoding="utf-8"))
    condicion_por_bloque = condiciones(analista)
    orden = sorted(muestra, key=lambda c: condicion_por_bloque[c["bloque"]] != "manual")
    archivo_nuevo = not REGISTROS.exists()
    with REGISTROS.open("a", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        if archivo_nuevo:
            escritor.writerow(COLUMNAS)
        print(f"Analista {analista}: {len(orden)} correos. Responda l (legítimo), s (spam) o p (phishing).")
        input("Pulse Enter para empezar.")
        for posicion, correo in enumerate(orden, 1):
            condicion = condicion_por_bloque[correo["bloque"]]
            _mostrar(correo, posicion, len(orden), condicion)
            inicio = time.perf_counter()
            respuesta = ""
            while respuesta not in OPCIONES:
                respuesta = input("Decisión [l/s/p]: ").strip().lower()
            segundos = round(time.perf_counter() - inicio, 2)
            sugerencia = correo["sugerencia"]["clase"] if condicion == "asistido" else ""
            fila = [analista, correo["id"], correo["bloque"], condicion, correo["clase_real"]]
            escritor.writerow([*fila, OPCIONES[respuesta], segundos, sugerencia])
            archivo.flush()
    print(f"\nSesión guardada en {REGISTROS}")


def _mediana(registros: list[dict], condicion: str) -> float:
    return statistics.median(r["segundos"] for r in registros if r["condicion"] == condicion)


def _acierto(registros: list[dict], condicion: str) -> float:
    filas = [r for r in registros if r["condicion"] == condicion]
    return round(100 * sum(r["decision"] == r["clase_real"] for r in filas) / len(filas), 1)


def _phishing_omitido(registros: list[dict], condicion: str) -> float | None:
    filas = [r for r in registros if r["condicion"] == condicion and r["clase_real"] == "phishing"]
    if not filas:
        return None
    return round(100 * sum(r["decision"] != "phishing" for r in filas) / len(filas), 1)


def _bootstrap_reduccion(registros: list[dict], remuestreos: int = 2000) -> list[float]:
    """Intervalo bootstrap al 95 % de la reducción de la mediana, remuestreando correos."""
    ids = sorted({r["id"] for r in registros})
    generador = random.Random(SEMILLA)
    reducciones = []
    for _ in range(remuestreos):
        elegidos = [generador.choice(ids) for _ in ids]
        manual = [r["segundos"] for i in elegidos for r in registros if r["id"] == i and r["condicion"] == "manual"]
        asistido = [r["segundos"] for i in elegidos for r in registros if r["id"] == i and r["condicion"] == "asistido"]
        if manual and asistido and statistics.median(manual) > 0:
            reducciones.append(1 - statistics.median(asistido) / statistics.median(manual))
    reducciones.sort()
    inferior = reducciones[int(0.025 * len(reducciones))]
    superior = reducciones[int(0.975 * len(reducciones)) - 1]
    return [round(100 * inferior, 1), round(100 * superior, 1)]


def resumen() -> None:
    with REGISTROS.open(encoding="utf-8") as archivo:
        registros = list(csv.DictReader(archivo))
    for r in registros:
        r["segundos"] = float(r["segundos"])

    por_analista = {}
    for analista in sorted({r["analista"] for r in registros}):
        propios = [r for r in registros if r["analista"] == analista]
        por_analista[analista] = {
            c: {"mediana_seg": _mediana(propios, c), "acierto_pct": _acierto(propios, c)}
            for c in ("manual", "asistido")
        }

    mediana_manual = _mediana(registros, "manual")
    mediana_asistido = _mediana(registros, "asistido")
    salida = {
        "n_registros": len(registros),
        "n_correos": len({r["id"] for r in registros}),
        "mediana_seg_manual": mediana_manual,
        "mediana_seg_asistido": mediana_asistido,
        "reduccion_tiempo_pct": round(100 * (1 - mediana_asistido / mediana_manual), 1),
        "ic95_reduccion_pct": _bootstrap_reduccion(registros),
        "acierto_pct": {c: _acierto(registros, c) for c in ("manual", "asistido")},
        "phishing_no_detectado_pct": {c: _phishing_omitido(registros, c) for c in ("manual", "asistido")},
        "por_analista": por_analista,
        "meta": "reducción >= 40 % (ambiciosa 60 %) sin aumentar el phishing no detectado (<= 5 %)",
        "naturaleza": "estimación con 20 correos y dos perfiles (experto y no experto en triaje)",
    }
    Path("triaje_resumen.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False, indent=1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Cronometraje del triaje manual frente al asistido")
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    subcomandos.add_parser("preparar").add_argument("csv")
    subcomandos.add_parser("sesion").add_argument("--analista", type=int, choices=[1, 2], required=True)
    subcomandos.add_parser("resumen")
    argumentos = parser.parse_args()
    if argumentos.comando == "preparar":
        preparar(argumentos.csv)
    elif argumentos.comando == "sesion":
        sesion(argumentos.analista)
    else:
        resumen()
    return 0


if __name__ == "__main__":
    sys.exit(main())
