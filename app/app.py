"""Interfaz web del detector híbrido de phishing (Streamlit).

Ejecución local, con la API levantada (ver deploy/README.md):

    G17_API_URL=http://localhost:8000 G17_API_KEY=<clave> streamlit run app/app.py

En ese modo la interfaz no carga modelos: consulta la API, que devuelve el contrato JSON v1.2. En la
demostración pública (``nube/streamlit_app.py``, modo ``local``) el mismo detector se carga dentro de
la interfaz. En ambos casos todo lo que se muestra (asunto, URL e IP) llega ya defangeado.

Variable de entorno adicional:
    G17_LIMITE_SESION   Análisis permitidos por sesión (0 = sin límite; la demostración usa 30).
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import cliente_api
from contenido import COLORES_CLASE, EJEMPLOS, LONGITUD_CORTA, METRICAS, TEXTOS

CARPETA = Path(__file__).resolve().parent
CLASES = ["legitimo", "spam", "phishing"]

st.set_page_config(
    page_title="Detector híbrido de phishing | G17",
    page_icon=str(CARPETA / "assets" / "icono.svg"),
    layout="wide",
)
st.markdown(f"<style>{(CARPETA / 'assets' / 'estilo.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def iniciar_estado() -> None:
    valores = {"historial": [], "ultimo": None, "asunto": "", "cuerpo": "", "aviso_corto": False, "n_analisis": 0}
    for clave, valor in valores.items():
        st.session_state.setdefault(clave, valor)


def en_la_nube() -> bool:
    """La demostración pública carga el modelo dentro de la interfaz (modo ``local``)."""
    return cliente_api.Configuracion.desde_entorno().modo == "local"


def limite_sesion() -> int:
    try:
        return max(0, int(os.getenv("G17_LIMITE_SESION", "0")))
    except ValueError:
        return 0


@st.cache_data(ttl=30, show_spinner=False)
def _estado_api() -> dict | None:
    return cliente_api.estado_servicio()


def estado_servicio() -> dict | None:
    # En la nube el estado se lee en memoria y cambia al terminar la carga: no se guarda en caché.
    return cliente_api.estado_servicio() if en_la_nube() else _estado_api()


def idioma_actual() -> str:
    return "en" if st.session_state.get("idioma_interfaz") == "English" else "es"


def clave_ejemplo(etiqueta: str) -> str:
    """Clave del ejemplo a partir de su nombre visible en cualquiera de los dos idiomas."""
    return next(clave for clave, ejemplo in EJEMPLOS.items() if etiqueta in (ejemplo["es"], ejemplo["en"]))


def cargar_ejemplo() -> None:
    ejemplo = EJEMPLOS[clave_ejemplo(st.session_state["ejemplo_elegido"])]
    st.session_state["asunto"] = ejemplo["asunto"]
    st.session_state["cuerpo"] = ejemplo["cuerpo"]
    st.session_state["ultimo"] = None


def limpiar() -> None:
    st.session_state["asunto"] = ""
    st.session_state["cuerpo"] = ""
    st.session_state["ultimo"] = None


def barra_lateral(t: dict) -> None:
    with st.sidebar:
        st.radio(t["idioma"], ["Español", "English"], key="idioma_interfaz", horizontal=True)
        st.subheader(t["estado"])
        salud = estado_servicio()
        nube = en_la_nube()
        if salud is None:
            st.error(t["estado_caido"])
        elif salud.get("estado") == "cargando":
            st.warning(t["estado_cargando_nube"])
        elif salud.get("estado") != "ok" and nube:
            st.error(t["estado_sin_modelo"])
        elif salud.get("estado") != "ok":
            st.warning(t["estado_cargando"])
        else:
            st.success(t["estado_ok_nube" if nube else "estado_ok"])
            servicio = f"API {salud['version_api']}" if salud.get("version_api") else t["inferencia_nube"]
            detalle = f"{salud.get('modelo')} {salud.get('variante')} | {servicio}"
            if salud.get("umbral_en") is not None:
                detalle += f" | {t['umbral'].lower()} {salud['umbral_en']:.4f}"
            st.caption(detalle)
        st.caption(t["privacidad_nube" if nube else "privacidad"])


def tarjeta_veredicto(resultado: dict, t: dict) -> None:
    clasificacion = resultado["clasificacion"]
    clase = clasificacion["clase"]
    nombre = t["nombres_clase"][clase]
    nivel = t["nombres_nivel"].get(clasificacion["nivel_riesgo"], clasificacion["nivel_riesgo"])
    st.markdown(
        f'<div class="veredicto" style="border-left-color:{COLORES_CLASE[clase]}">'
        f'<div class="veredicto-etiqueta">{t["clase"]}</div>'
        f'<div class="veredicto-clase">{nombre}</div>'
        f'<div class="veredicto-detalle">{t["riesgo"]} {clasificacion["riesgo"]}/100 · {t["nivel"]} {nivel}</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.progress(clasificacion["riesgo"] / 100)


def grafico_probabilidades(resultado: dict, t: dict) -> alt.Chart:
    probabilidades = resultado["clasificacion"]["probabilidades"]
    datos = pd.DataFrame({
        "clase": [t["nombres_clase"][c] for c in CLASES],
        "probabilidad": [probabilidades[c] for c in CLASES],
    })
    escala = alt.Scale(domain=[t["nombres_clase"][c] for c in CLASES], range=[COLORES_CLASE[c] for c in CLASES])
    base = alt.Chart(datos).encode(
        y=alt.Y("clase:N", sort=None, title=None),
        x=alt.X("probabilidad:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"), title=None),
    )
    barras = base.mark_bar(cornerRadiusEnd=4, height=22).encode(
        color=alt.Color("clase:N", scale=escala, legend=None),
        tooltip=[alt.Tooltip("clase:N"), alt.Tooltip("probabilidad:Q", format=".2%")],
    )
    # Gris medio: legible sobre el fondo claro y sobre el oscuro
    etiquetas = base.mark_text(align="left", dx=4, color="#8a8984").encode(
        text=alt.Text("probabilidad:Q", format=".1%"))
    return (barras + etiquetas).properties(height=140)


def tabla_ramas(resultado: dict, t: dict) -> pd.DataFrame:
    ramas = resultado["ramas"]
    filas = []
    for nombre, valores in ((t["rama_bert"], ramas["texto_distilbert"]), (t["rama_base"], ramas["texto_baseline"])):
        if valores is None:
            filas.append({t["rama"]: nombre, **{t["nombres_clase"][c]: t["no_aplica"] for c in CLASES}})
        else:
            filas.append({t["rama"]: nombre, **{t["nombres_clase"][c]: f"{valores[c]:.1%}" for c in CLASES}})
    url = ramas["url"]
    valor_url = "-" if url["max"] is None else f"{url['max']:.1%}"
    filas.append({t["rama"]: t["rama_url"], t["nombres_clase"]["legitimo"]: "",
                  t["nombres_clase"]["spam"]: "", t["nombres_clase"]["phishing"]: valor_url})
    return pd.DataFrame(filas)


def recomendacion(resultado: dict, t: dict) -> str:
    if "idioma_no_soportado" in resultado["advertencias"]:
        return t["rec_revision"]
    return t[f"rec_{resultado['clasificacion']['clase']}"]


def mostrar_resultado(resultado: dict, t: dict) -> None:
    st.subheader(t["resultado"])
    if "idioma_no_soportado" in resultado["advertencias"]:
        st.warning(t["aviso_idioma"].format(idioma=resultado["idioma_detectado"]))
    if st.session_state.get("aviso_corto"):
        st.warning(t["aviso_corto"].format(n=LONGITUD_CORTA))

    izquierda, derecha = st.columns([1, 1.4], gap="large")
    with izquierda:
        tarjeta_veredicto(resultado, t)
        st.markdown(f"**{t['recomendacion']}.** {recomendacion(resultado, t)}")
    with derecha:
        st.markdown(f"**{t['probabilidades']}**")
        st.altair_chart(grafico_probabilidades(resultado, t), width="stretch")

    columnas = st.columns(4)
    columnas[0].metric(t["ruta"], resultado["ruta_modelo"])
    columnas[1].metric(t["idioma_detectado"], resultado["idioma_detectado"])
    columnas[2].metric(t["umbral"], numero_local(f"{resultado['modelo']['umbral_phishing']:.2f}"))
    columnas[3].metric(t["latencia"], f"{resultado['latencia_ms']:.0f} ms")

    with st.expander(t["ramas"]):
        st.dataframe(tabla_ramas(resultado, t), hide_index=True, width="stretch")
        if resultado["ramas"]["url"]["sin_url"]:
            st.caption(t["sin_url"])

    with st.expander(t["iocs"], expanded=resultado["clasificacion"]["clase"] == "phishing"):
        iocs = resultado["iocs"]["urls"] + resultado["iocs"]["ips"]
        if iocs:
            st.code("\n".join(iocs), language=None)
        else:
            st.caption(t["sin_iocs"])
        if resultado["mitre_attack"]:
            tecnicas = ", ".join(f"{m['tecnica']} {m['nombre']}" for m in resultado["mitre_attack"])
            st.markdown(f"**{t['mitre']}:** {tecnicas}")

    st.download_button(t["descargar_json"], json.dumps(resultado, ensure_ascii=False, indent=2),
                       file_name=f"analisis_{resultado['id_analisis']}.json", mime="application/json")


def ejecutar_analisis(t: dict, archivo) -> None:
    eml = archivo.getvalue() if archivo is not None else None
    asunto, cuerpo = st.session_state["asunto"], st.session_state["cuerpo"]
    limite = limite_sesion()
    if limite and st.session_state["n_analisis"] >= limite:
        st.error(t["error_limite"].format(n=limite))
        return
    problemas = cliente_api.validar_entrada(asunto, cuerpo, eml)
    if problemas:
        for problema in problemas:
            st.error(t[f"error_{problema}"])
        return
    with st.spinner(t["procesando"]):
        try:
            resultado = cliente_api.analizar(asunto, cuerpo, eml)
        except cliente_api.ErrorAPI as error:
            st.error(t.get(f"error_{error.codigo}", t["error_error_servidor"]))
            return
    st.session_state["n_analisis"] += 1
    st.session_state["aviso_corto"] = eml is None and len(f"{asunto} {cuerpo}".strip()) < LONGITUD_CORTA
    st.session_state["ultimo"] = resultado
    hora_utc = dt.datetime.now(dt.UTC).strftime("%H:%M:%S")
    st.session_state["historial"].append({"hora": hora_utc, "resultado": resultado})


def pestana_analizar(t: dict) -> None:
    columna_ejemplo, columna_boton = st.columns([3, 1], vertical_alignment="bottom")
    etiquetas = [ejemplo[idioma_actual()] for ejemplo in EJEMPLOS.values()]
    columna_ejemplo.selectbox(t["ejemplo"], etiquetas, key="ejemplo_elegido")
    columna_boton.button(t["boton_ejemplo"], on_click=cargar_ejemplo, width="stretch")

    texto, archivo_eml = st.tabs([t["modo_texto"], t["modo_eml"]])
    with texto:
        st.text_input(t["asunto"], key="asunto", max_chars=cliente_api.MAX_CARACTERES_ASUNTO)
        st.text_area(t["cuerpo"], key="cuerpo", height=240, help=t["ayuda_cuerpo"])
        st.caption(f"{len(st.session_state['cuerpo']):,} {t['caracteres']}".replace(",", "."))
    with archivo_eml:
        archivo = st.file_uploader(t["archivo"], type=["eml"])
        st.caption(t["prioridad_eml"])

    boton_analizar, boton_limpiar, _ = st.columns([1, 1, 4])
    analizar = boton_analizar.button(t["boton_analizar"], type="primary", width="stretch")
    boton_limpiar.button(t["boton_limpiar"], on_click=limpiar, width="stretch")
    if analizar:
        ejecutar_analisis(t, archivo)
    if st.session_state["ultimo"] is not None:
        st.divider()
        mostrar_resultado(st.session_state["ultimo"], t)


def tabla_historial(t: dict) -> pd.DataFrame:
    filas = []
    for numero, entrada in enumerate(st.session_state["historial"], 1):
        r = entrada["resultado"]
        filas.append({
            "#": numero,
            t["hora"]: entrada["hora"],
            t["asunto"]: r["correo"]["asunto_defang"],
            t["clase"]: t["nombres_clase"][r["clasificacion"]["clase"]],
            t["riesgo"]: r["clasificacion"]["riesgo"],
            t["nivel"]: t["nombres_nivel"].get(r["clasificacion"]["nivel_riesgo"], r["clasificacion"]["nivel_riesgo"]),
            t["ruta"]: r["ruta_modelo"],
            f"{t['latencia']} (ms)": round(r["latencia_ms"]),
            "id_analisis": r["id_analisis"],
        })
    return pd.DataFrame(filas)


def pestana_historial(t: dict) -> None:
    if not st.session_state["historial"]:
        st.info(t["historial_vacio"])
        return
    tabla = tabla_historial(t)
    st.dataframe(tabla, hide_index=True, width="stretch")
    escala = alt.Scale(domain=[t["nombres_clase"][c] for c in CLASES], range=[COLORES_CLASE[c] for c in CLASES])
    grafico = alt.Chart(tabla).mark_bar(cornerRadiusEnd=4, size=36).encode(
        x=alt.X("#:O", title="#", axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{t['riesgo']}:Q", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color(f"{t['clase']}:N", scale=escala),
        tooltip=list(tabla.columns[:-1]),
    ).properties(height=260, title=t["comparacion"])
    st.altair_chart(grafico, width="stretch")
    columna_csv, columna_borrar, _ = st.columns([1.4, 1, 2])
    columna_csv.download_button(t["descargar_csv"], tabla.to_csv(index=False).encode("utf-8"),
                                file_name="historial_analisis.csv", mime="text/csv", width="stretch")
    if columna_borrar.button(t["limpiar_historial"], width="stretch"):
        st.session_state["historial"] = []
        st.rerun()


def numero_local(texto: str) -> str:
    """En español, coma decimal y espacio antes del signo de porcentaje (96,4 %)."""
    if idioma_actual() != "es":
        return texto
    return texto.replace(".", ",").replace("%", " %").replace("  %", " %")


def pestana_acerca(t: dict) -> None:
    st.markdown(t["acerca"])
    tabla = pd.DataFrame({
        t["metrica"]: list(t["tabla_metricas"]),
        t["valor"]: [numero_local(formato.format(**METRICAS)) for formato in t["tabla_metricas"].values()],
    })
    st.dataframe(tabla, hide_index=True, width="stretch")
    st.markdown(t["limitaciones"])


def main() -> None:
    iniciar_estado()
    t = TEXTOS[idioma_actual()]
    barra_lateral(t)
    st.title(t["titulo"])
    st.caption(t["subtitulo"])
    analizar, historial, acerca, ayuda = st.tabs(
        [t["pestana_analizar"], t["pestana_historial"], t["pestana_acerca"], t["pestana_ayuda"]])
    with analizar:
        pestana_analizar(t)
    with historial:
        pestana_historial(t)
    with acerca:
        pestana_acerca(t)
    with ayuda:
        st.markdown(t["ayuda"])


main()
