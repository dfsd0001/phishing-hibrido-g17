"""Pruebas de lectura de correos y del texto de entrada de los modelos."""

import email.message
import hashlib

import pandas as pd
import pytest

from src.data_processing import (
    anio_de,
    aplicar_pliegue,
    construir_dataset,
    hash_normalizado,
    marcar_exclusiones,
    particion_estratificada,
    pliegues_fuera_de_distribucion,
    texto_de_email,
    texto_para_modelo,
    texto_plano,
)
from src.ioc_utils import defang_texto, iocs_vivos
from src.utils import cargar_config


def test_texto_plano_quita_html_y_script():
    assert texto_plano("<p>Hola&nbsp;<b>mundo</b></p><script>x=1</script>") == "Hola mundo"


def test_hash_ignora_formato_y_mayusculas():
    assert hash_normalizado("<p>Hola  Mundo</p>") == hash_normalizado("hola mundo")


def test_anio_de_encabezado():
    assert anio_de("Tue, 14 Mar 2023 10:00:00 +0000") == 2023
    assert anio_de("sin fecha") is None


def test_parser_conserva_href_e_ignora_adjuntos():
    mensaje = email.message.EmailMessage()
    mensaje["Subject"] = "Aviso"
    mensaje["Date"] = "Mon, 1 Jan 2024 00:00:00 +0000"
    mensaje.set_content("texto")
    mensaje.add_alternative('<a href="https://pay.example.com">x</a>', subtype="html")
    mensaje.add_attachment(b"MZ", maintype="application", subtype="octet-stream", filename="a.exe")
    resultado = texto_de_email(mensaje.as_bytes())
    assert 'href="https://pay.example.com"' in resultado["body"]
    assert resultado["subject"] == "Aviso"
    assert "MZ" not in resultado["body"]


def test_texto_para_modelo_usa_marcadores():
    crudo = (
        '<p>Dear user, verify at <a href="https://pay.example.com/x">https://pay.example.com/x</a> '
        "or www.example.org, server 192.0.2.7. Contact admin@example.com before March 2024.</p>"
    )
    resultado = texto_para_modelo(defang_texto(crudo))
    for marcador in ("__url__", "__ip__", "__email__", "__anio__"):
        assert marcador in resultado
    assert "example" not in resultado
    assert "2024" not in resultado
    assert "<" not in resultado
    assert iocs_vivos(resultado) == []


def test_texto_para_modelo_conserva_numeros_comunes():
    assert texto_para_modelo("pay 1500 USD, ref 12345") == "pay 1500 USD, ref 12345"


@pytest.mark.parametrize(
    "crudo",
    ["To: phishing@pot, Dear user", "cc arphishing@pot-f-p, hola", "enviar a phishing@ ahora"],
)
def test_direcciones_sin_punto_se_enmascaran(crudo):
    """Regresión de fuga de etiqueta: la dirección del honeypot delataba la clase."""
    resultado = texto_para_modelo(defang_texto(crudo))
    assert "phishing" not in resultado
    assert "__email__" in resultado


def test_rachas_de_simbolos_se_acortan():
    assert texto_para_modelo("WIN!!!!!!!! now ______________ end") == "WIN!!! now ___ end"


def test_dominio_propio_se_enmascara():
    resultado = texto_para_modelo("Your Monkey.org mailbox is full. monkey Webmail team", ["monkey.org", "monkey"])
    assert "monkey" not in resultado.lower()
    assert resultado.count("__dominio_propio__") == 2


def test_sin_dominio_propio_no_se_modifica_el_texto():
    assert "monkey" in texto_para_modelo("monkey business")


# Preparación del dataset (notebook 02)


@pytest.fixture
def reglas():
    return cargar_config()["preparacion"]


def _correo(grupo, clase, clave, longitud=200, idioma="en", anio=2020, fuente=None):
    """Correo sintético; la huella es el SHA-1 de ``clave``, como en el pipeline real."""
    return {
        "grupo": grupo,
        "fuente": fuente or f"kaggle/{grupo}",
        "clase": clase,
        "hash": hashlib.sha1(clave.encode()).hexdigest(),
        "len_plano": longitud,
        "idioma": idioma,
        "anio": anio,
        "texto_defang": f"mensaje {clave} de {grupo}",
    }


def test_exclusiones_en_orden_y_sin_solapamiento(reglas):
    correos = pd.DataFrame(
        [
            _correo("Enron", "legitimo", "a1", longitud=5),
            _correo("CEAS_08", "spam", "b1", longitud=5),
            _correo("phishing_pot", "phishing", "c1", idioma="pt"),
            _correo("CEAS_08", "legitimo", "d1"),
            _correo("SpamAssasin", "legitimo", "d1"),
            _correo("SpamAssasin", "spam", "e1"),
        ]
    )
    tabla, bitacora = marcar_exclusiones(correos, reglas)
    assert bitacora == {"grupo_excluido": 1, "casi_vacio": 1, "idioma": 1, "duplicado": 1}
    # El duplicado conservado es el primero en el orden determinista (CEAS_08 antes que SpamAssasin)
    conservados = tabla[tabla["motivo_exclusion"].isna()]
    assert set(conservados["grupo"]) == {"CEAS_08", "SpamAssasin"}
    assert conservados.loc[conservados["grupo"] == "CEAS_08", "clase"].item() == "legitimo"
    assert conservados.loc[conservados["grupo"] == "SpamAssasin", "clase"].item() == "spam"


def test_construir_dataset_exige_dos_origenes_por_clase(reglas):
    filas = [_correo("CEAS_08", "legitimo", f"l{i}") for i in range(3)]
    filas += [_correo("CEAS_08", "spam", f"s{i}") for i in range(3)]
    filas += [_correo("nazario_anual", "phishing", f"p{i}") for i in range(3)]
    tabla, _ = marcar_exclusiones(pd.DataFrame(filas), reglas)
    with pytest.raises(ValueError):
        construir_dataset(tabla, reglas)


def test_construir_dataset_enmascara_el_dominio_propio(reglas):
    filas = [_correo(g, "legitimo", f"{g}l{i}") for g in ("CEAS_08", "SpamAssasin") for i in range(2)]
    filas += [_correo(g, "spam", f"{g}s{i}") for g in ("CEAS_08", "SpamAssasin") for i in range(2)]
    filas += [_correo(g, "phishing", f"{g}p{i}") for g in ("nazario_anual", "phishing_pot") for i in range(2)]
    filas[-3]["texto_defang"] = "message from jose at monkey.org"
    tabla, _ = marcar_exclusiones(pd.DataFrame(filas), reglas)
    datos = construir_dataset(tabla, reglas)
    nazario = datos[datos["grupo"] == "nazario_anual"]["texto_modelo"]
    assert nazario.str.contains("__dominio_propio__").any()
    assert not datos["texto_modelo"].str.contains("monkey").any()
    assert set(datos["y"]) == {0, 1, 2}
    assert datos["id"].str.len().eq(16).all()


def test_particion_estratificada_y_pliegues(reglas):
    filas = []
    for grupo, clase in [("CEAS_08", "legitimo"), ("CEAS_08", "spam"), ("nazario_anual", "phishing")]:
        for i in range(100):
            filas.append(_correo(grupo, clase, f"{grupo}{clase}{i}", anio=2024 + i % 2))
    datos = pd.DataFrame(filas)
    particion = particion_estratificada(datos, reglas["proporciones"], 17)
    conteo = particion.value_counts()
    assert conteo.sum() == 300
    assert abs(conteo["train"] - 210) <= 1 and abs(conteo["val"] - conteo["test"]) <= 1
    # Cada clase conserva su proporción en las tres particiones
    assert (pd.crosstab(particion, datos["clase"]).min(axis=1) >= 14).all()
    assert particion.equals(particion_estratificada(datos, reglas["proporciones"], 17))
    pliegues = pliegues_fuera_de_distribucion(datos, reglas["anio_corte_temporal"])
    assert set(pliegues) == {"loso_CEAS_08", "loso_nazario_anual", "temporal_phishing_2025+"}
    pliegue = aplicar_pliegue(particion, pliegues["loso_nazario_anual"])
    assert (pliegue[datos["grupo"] == "nazario_anual"] == "test").all()
    assert (pliegue[datos["grupo"] != "nazario_anual"] == particion[datos["grupo"] != "nazario_anual"]).all()
