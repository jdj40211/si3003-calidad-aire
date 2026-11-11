"""Dashboard de calidad del aire del Valle de Aburrá (Streamlit).

Integrante 3: Juan José Palacio.

Cuatro vistas: mapa de estaciones, serie de tiempo con parámetros, predicción del
día siguiente (modelo de la Parte 1) y chat con el agente (RAG de la Parte 2).

Se ejecuta con:
    streamlit run app/dashboard.py

Las vistas de predicción y chat consumen los módulos del equipo. Si alguno no está
disponible, la vista muestra un aviso en vez de romperse.
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

PROCESADOS = RAIZ / "data" / "processed"

COLOR_ICA = {
    "Buena": "#2ecc71",
    "Aceptable": "#f1c40f",
    "Dañina sensibles": "#e67e22",
    "Dañina": "#e74c3c",
    "Muy dañina": "#8e44ad",
    "Peligrosa": "#7b241c",
}
ORDEN_ICA = list(COLOR_ICA.keys())

st.set_page_config(page_title="Calidad del aire — Valle de Aburrá", page_icon="🌫️", layout="wide")

@st.cache_data(show_spinner=False)
def cargar_pm25() -> pd.DataFrame:
    df = pd.read_csv(PROCESADOS / "pm25_diario.csv", parse_dates=["dia"])
    df["ica"] = pd.Categorical(df["ica"], categories=ORDEN_ICA, ordered=True)
    return df

@st.cache_data(show_spinner=False)
def cargar_estaciones() -> pd.DataFrame:
    return pd.read_csv(PROCESADOS / "estaciones.csv")

def aviso_datos_faltantes(e: Exception) -> None:
    st.error(
        "No se encontraron los datos procesados. Ejecuta primero el pipeline de datos:\n\n"
        "```\npython -m src.datos.descargar\npython -m src.datos.procesar\n```"
    )
    st.caption(f"Detalle: {e}")

def vista_mapa(df: pd.DataFrame, estaciones: pd.DataFrame) -> None:
    st.subheader("Mapa de estaciones")
    st.caption("Cada punto es una estación, coloreada por su última categoría de calidad del aire (ICA).")

    ultimos = df.sort_values("dia").groupby("estacion").tail(1)
    mapa = estaciones.merge(ultimos[["estacion", "dia", "pm25", "ica"]], on="estacion", how="left")
    mapa["ica"] = mapa["ica"].astype("object").fillna("Sin dato")
    mapa["color"] = mapa["ica"].map(COLOR_ICA).fillna("#95a5a6")
    mapa["fecha"] = mapa["dia"].dt.date.astype("string").fillna("—")

    try:
        import plotly.express as px

        fig = px.scatter_mapbox(
            mapa, lat="latitud", lon="longitud", color="ica",
            color_discrete_map={**COLOR_ICA, "Sin dato": "#95a5a6"},
            hover_name="estacion",
            hover_data={"municipio": True, "pm25": True, "fecha": True,
                        "latitud": False, "longitud": False, "ica": True},
            size_max=18, zoom=10, height=560,
            category_orders={"ica": ORDEN_ICA + ["Sin dato"]},
        )
        fig.update_traces(marker={"size": 14})
        fig.update_layout(mapbox_style="carto-positron", margin={"l": 0, "r": 0, "t": 10, "b": 0},
                          legend_title_text="Categoría ICA")
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.map(mapa.rename(columns={"latitud": "lat", "longitud": "lon"})[["lat", "lon"]])

    st.dataframe(
        mapa[["estacion", "municipio", "pm25", "ica", "fecha"]]
        .rename(columns={"estacion": "Estación", "municipio": "Municipio",
                         "pm25": "PM2.5 (µg/m³)", "ica": "Categoría", "fecha": "Fecha"}),
        use_container_width=True, hide_index=True,
    )

def vista_serie(df: pd.DataFrame) -> None:
    st.subheader("Serie de tiempo de PM2.5")

    estaciones = ["Promedio del valle"] + sorted(df["estacion"].unique())
    col1, col2 = st.columns([2, 3])
    with col1:
        seleccion = st.selectbox("Estación", estaciones)
    min_d, max_d = df["dia"].min().date(), df["dia"].max().date()
    with col2:
        rango = st.slider("Rango de fechas", min_value=min_d, max_value=max_d,
                          value=(max(min_d, max_d - timedelta(days=365)), max_d))

    inicio, fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
    recorte = df[(df["dia"] >= inicio) & (df["dia"] <= fin)]

    if seleccion == "Promedio del valle":
        serie = recorte.groupby("dia")["pm25"].mean().reset_index()
        titulo = "PM2.5 promedio del valle"
    else:
        serie = recorte[recorte["estacion"] == seleccion][["dia", "pm25"]]
        titulo = f"PM2.5 — {seleccion}"

    if serie.empty:
        st.info("No hay datos en el rango seleccionado.")
        return

    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=serie["dia"], y=serie["pm25"], mode="lines",
                                 name="PM2.5", line={"color": "#2c7fb8"}))
        for y, txt, color in [(12.0, "Buena/Aceptable", "#2ecc71"),
                              (37.0, "Dañina a sensibles", "#e67e22"),
                              (55.0, "Dañina a la salud", "#e74c3c")]:
            fig.add_hline(y=y, line_dash="dash", line_color=color,
                          annotation_text=txt, annotation_position="right")
        fig.update_layout(title=titulo, xaxis_title="Fecha", yaxis_title="PM2.5 (µg/m³)",
                          height=480, margin={"t": 50})
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.line_chart(serie.set_index("dia")["pm25"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Promedio del periodo", f"{serie['pm25'].mean():.1f} µg/m³")
    c2.metric("Máximo", f"{serie['pm25'].max():.1f} µg/m³")
    c3.metric("Días con dato", f"{len(serie)}")

def vista_prediccion() -> None:
    st.subheader("Predicción para el día siguiente")
    st.caption("Categoría de calidad del aire prevista con el modelo de la Parte 1 (Random Forest).")

    try:
        from src.modelo.predecir import predecir_manana

        pred = predecir_manana()
    except Exception as e:  # noqa: BLE001
        st.warning("La predicción no está disponible todavía (modelo de la Parte 1 en construcción).")
        st.caption(f"Detalle técnico: {e}")
        return

    categoria = pred["categoria_predicha"]
    color = {0: "#2ecc71", 1: "#f1c40f", 2: "#e74c3c"}.get(pred["clase_predicha"], "#95a5a6")
    st.markdown(
        f"<div style='padding:1rem;border-radius:8px;background:{color};color:#111;"
        f"font-size:1.3rem;font-weight:600'>Mañana: {categoria}</div>",
        unsafe_allow_html=True,
    )
    st.write(f"Base de la predicción: último día con datos ({pred['fecha_base']}).")

    c1, c2 = st.columns(2)
    c1.metric("PM2.5 promedio de hoy", f"{pred['pm25_mean_hoy']} µg/m³")
    c2.metric("PM2.5 máximo de hoy", f"{pred['pm25_max_hoy']} µg/m³")

    probs = pd.DataFrame(
        {"Categoría": list(pred["probabilidades"].keys()),
         "Probabilidad": list(pred["probabilidades"].values())}
    )
    st.bar_chart(probs.set_index("Categoría"))

    metricas_path = RAIZ / "eval" / "metricas_modelo.json"
    if metricas_path.exists():
        import json

        m = json.loads(metricas_path.read_text(encoding="utf-8"))
        st.caption(
            f"Desempeño en prueba — modelo: {m.get('accuracy_modelo')} de accuracy "
            f"vs. línea base de persistencia: {m.get('accuracy_baseline')} "
            f"(F1 macro del modelo: {m.get('f1_macro_modelo')})."
        )

def vista_chat() -> None:
    st.subheader("Chat con el agente")
    st.caption("Pregunta por el PM2.5, la predicción o la normativa. El agente cita sus fuentes.")

    try:
        from src.agente.agente import AgenteCalidadAire

        agente = AgenteCalidadAire()
    except Exception as e:  # noqa: BLE001
        st.warning("El agente no está disponible todavía (Parte 2 en construcción).")
        st.caption(f"Detalle técnico: {e}")
        return

    ejemplos = [
        "¿Qué significa la categoría dañina para grupos sensibles?",
        "¿Cómo estará la calidad del aire mañana?",
        "¿Qué recomiendan para hacer ejercicio cuando hay alerta naranja?",
    ]
    st.write("Ejemplos: " + " · ".join(f"*{e}*" for e in ejemplos))

    if "historial" not in st.session_state:
        st.session_state.historial = []

    for turno in st.session_state.historial:
        with st.chat_message(turno["rol"]):
            st.markdown(turno["texto"])

    pregunta = st.chat_input("Escribe tu pregunta...")
    if pregunta:
        st.session_state.historial.append({"rol": "user", "texto": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Consultando datos y documentos..."):
                traza = agente.responder(pregunta)
            st.markdown(traza.respuesta)
            if traza.herramientas_usadas:
                st.caption("Herramientas usadas: " + ", ".join(traza.herramientas_usadas))
        st.session_state.historial.append({"rol": "assistant", "texto": traza.respuesta})

def main() -> None:
    st.title("🌫️ Calidad del aire del Valle de Aburrá")
    st.caption(
        "Monitoreo de PM2.5, predicción de la categoría del día siguiente y asistente con RAG. "
        "Proyecto SI3003 — Universidad EAFIT, 2026-2."
    )

    try:
        df = cargar_pm25()
        estaciones = cargar_estaciones()
    except Exception as e:  # noqa: BLE001
        aviso_datos_faltantes(e)
        return

    with st.sidebar:
        st.header("Resumen")
        ultimo_dia = df["dia"].max().date()
        pm_valle = df[df["dia"] == df["dia"].max()]["pm25"].mean()
        st.metric("Último día con datos", str(ultimo_dia))
        st.metric("PM2.5 promedio ese día", f"{pm_valle:.1f} µg/m³")
        st.metric("Estaciones", f"{df['estacion'].nunique()}")
        st.divider()
        st.caption("Herramienta académica. No reemplaza los avisos oficiales del SIATA ni del AMVA.")

    tab_mapa, tab_serie, tab_pred, tab_chat = st.tabs(
        ["🗺️ Mapa", "📈 Serie de tiempo", "🔮 Predicción", "💬 Chat"]
    )
    with tab_mapa:
        vista_mapa(df, estaciones)
    with tab_serie:
        vista_serie(df)
    with tab_pred:
        vista_prediccion()
    with tab_chat:
        vista_chat()

if __name__ == "__main__":
    main()
