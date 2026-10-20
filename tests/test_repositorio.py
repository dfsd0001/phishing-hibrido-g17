"""Controles de seguridad sobre el propio repositorio.

1. Ningún archivo de texto contiene IOC vivos fuera de los dominios reservados para pruebas
   (RFC 2606 y RFC 6761), los rangos IPv4 de documentación (RFC 5737), los servicios internos
   del despliegue y los sitios de referencia citados en la documentación.
2. No se versionan archivos con secretos (``.env``) ni claves con forma de token.
"""

import re
import subprocess
from pathlib import Path

import pytest

from src.ioc_utils import iocs_vivos

RAIZ = Path(__file__).resolve().parents[1]
EXTENSIONES = {".py", ".md", ".yaml", ".yml", ".json", ".txt", ".ipynb", ".toml", ".cfg", ""}
EXCLUIR = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "data", "models"}

HOSTS_PERMITIDOS = re.compile(
    r"""^(
        (.+\.)?example\.(com|net|org)
      | .+\.(test|invalid|example)
      | localhost
      | api | app | n8n | wazuh | ui
      | (www\.)?(github\.com|huggingface\.co|kaggle\.com|archive\.ics\.uci\.edu|zenodo\.org
        |doi\.org|arxiv\.org|attack\.mitre\.org|json-schema\.org|streamlit\.io|docs\.n8n\.io
        |documentation\.wazuh\.com|docs\.dfir-iris\.org|spamassassin\.apache\.org|python\.org
        |scikit-learn\.org|optuna\.org|fairlearn\.org|img\.shields\.io|opensource\.org
        |raw\.githubusercontent\.com|spdp\.gob\.ec|eur-lex\.europa\.eu|nist\.gov|www\.nist\.gov
        |dl\.acm\.org|ieeexplore\.ieee\.org|docs\.docker\.com|pypi\.org|w3\.org|www\.w3\.org
        |colab\.research\.google\.com|api\.github\.com|codeload\.github\.com|monkey\.org
        |nlp\.stanford\.edu|download\.pytorch\.org|malware-traffic-analysis\.net)
    )$""",
    re.VERBOSE,
)
IP_PERMITIDA = re.compile(r"^(192\.0\.2\.|198\.51\.100\.|203\.0\.113\.|127\.0\.0\.1$|0\.0\.0\.0$)")
TOKEN = re.compile(r"\b(hf_[A-Za-z0-9]{30,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,})\b")


def _archivos_de_texto():
    for ruta in RAIZ.rglob("*"):
        if ruta.is_file() and not EXCLUIR.intersection(ruta.relative_to(RAIZ).parts) and ruta.suffix in EXTENSIONES:
            yield ruta


def _permitido(ioc: str) -> bool:
    """Un IOC es aceptable si todos los hosts e IPv4 que contiene son reservados o de referencia."""
    piezas = re.split(r"(?i)(?<=[^\s/:])(?=(?:https?|ftp)://)", ioc)
    if len(piezas) > 1:
        return all(_permitido(p) for p in piezas)
    ips = re.findall(r"\d{1,3}(?:\.\d{1,3}){3}", ioc)
    hosts = re.findall(r"(?i)(?:[a-z0-9*\u00c0-\uffff-]+\.)+[a-z\u00c0-\uffff]{2,}", ioc)
    hosts = [h.lower().lstrip("*.") for h in hosts if not re.fullmatch(r"[\d.]+", h)]
    # Las rutas de archivo (p. ej. "login.verify") no son hosts: solo cuenta la autoridad.
    autoridad = re.sub(r"(?i)^(?:[a-z]+://)+", "", ioc).split("/", 1)[0].split(",", 1)[0]
    hosts = [h for h in hosts if h in autoridad.lower() or "://" + h in ioc.lower()]
    return all(IP_PERMITIDA.match(ip) for ip in ips) and all(HOSTS_PERMITIDOS.match(h) for h in hosts)


@pytest.mark.parametrize("ruta", sorted(_archivos_de_texto()), ids=lambda r: str(r.relative_to(RAIZ)))
def test_sin_iocs_reales(ruta):
    texto = ruta.read_text(encoding="utf-8", errors="ignore")
    no_permitidos = sorted({ioc for ioc in iocs_vivos(texto) if not _permitido(ioc)})
    assert no_permitidos == [], f"IOC vivo fuera de la lista permitida en {ruta.name}: {no_permitidos[:5]}"


@pytest.mark.parametrize("ruta", sorted(_archivos_de_texto()), ids=lambda r: str(r.relative_to(RAIZ)))
def test_sin_tokens(ruta):
    assert not TOKEN.search(ruta.read_text(encoding="utf-8", errors="ignore"))


def test_env_no_versionado():
    try:
        versionados = subprocess.run(
            ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("El directorio no es un repositorio git")
    assert not [f for f in versionados if Path(f).name == ".env"]
