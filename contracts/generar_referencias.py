"""Regenera los archivos de referencia del contrato con el detector simulado de las pruebas.

Uso (desde la raíz del repositorio):
    python -m contracts.generar_referencias

Los archivos muestran el formato de la salida; sus probabilidades no provienen del modelo real.
"""

import json
from pathlib import Path

from tests.simulados import VALIDADOR, detector_bilingue

CASOS = {
    "phishing": (
        "Account suspended",
        "Dear user, verify your password at hxxps[://]secure-login[.]example[.]com/verify?id=7 or "
        "192[.]0[.]2[.]4 today, otherwise your mailbox will be permanently deleted.",
    ),
    "spam": ("Oferta", "Gran oferta de relojes, visite www[.]tienda[.]example[.]net/promo y aproveche el descuento."),
    "legitimo": (
        "Reunión de equipo",
        "Hola equipo, nos vemos el martes a las diez para revisar el informe trimestral del proyecto.",
    ),
}


def main() -> None:
    detector = detector_bilingue()
    destino = Path(__file__).resolve().parent / "golden"
    for nombre, (asunto, cuerpo) in CASOS.items():
        salida = detector.analizar(asunto, cuerpo)
        VALIDADOR.validate(salida)
        (destino / f"{nombre}.json").write_text(json.dumps(salida, indent=2, ensure_ascii=False) + "\n")
        print(nombre, salida["ruta_modelo"], salida["clasificacion"]["clase"])


if __name__ == "__main__":
    main()
