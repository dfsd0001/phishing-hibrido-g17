"""Pruebas estáticas del flujo de n8n versionado en ``deploy/n8n``."""

import json
from pathlib import Path

from deploy.n8n.generar_flujo import construir

RAIZ = Path(__file__).resolve().parents[1]
FLUJO = json.loads((RAIZ / "deploy" / "n8n" / "g17_flujo_triaje.json").read_text(encoding="utf-8"))


def test_el_archivo_versionado_coincide_con_el_generador():
    """Evita editar el JSON a mano y olvidar regenerarlo desde ``codigo/*.js``."""
    assert construir() == FLUJO


def test_todas_las_conexiones_apuntan_a_nodos_existentes():
    nombres = {nodo["name"] for nodo in FLUJO["nodes"]}
    for origen, salidas in FLUJO["connections"].items():
        assert origen in nombres
        for rama in salidas["main"]:
            for enlace in rama:
                assert enlace["node"] in nombres


def test_el_flujo_no_contiene_claves():
    """Las claves se leen de variables de entorno, nunca se escriben en el flujo."""
    texto = json.dumps(FLUJO)
    assert "$env.G17_API_KEY" in texto
    assert "$env.IRIS_API_KEY" in texto
    for patron in ("hf_", "Bearer ey", 'password": "'):
        assert patron not in texto


def test_el_fallo_de_la_api_nunca_cierra_el_caso():
    api = next(n for n in FLUJO["nodes"] if n["name"] == "Analizar (API G17)")
    assert api["onError"] == "continueErrorOutput"
    assert len(FLUJO["connections"]["Analizar (API G17)"]["main"]) == 2
