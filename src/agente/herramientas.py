"""Herramientas del agente de calidad del aire.

- get_pm25(estacion=None, dias=7): últimas mediciones de PM2.5 (una estación o el valle).
- predict_tomorrow(): categoría ICA prevista para el día siguiente (modelo de la Parte 1).
- search_docs(consulta, k=3): fragmentos del corpus (normativa, protocolos, salud) con su fuente.

Todas capturan sus propios errores y devuelven {"error": ...} en vez de lanzar excepciones.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .rag import BaseConocimiento

RAIZ = Path(__file__).resolve().parents[2]
PROCESADOS = RAIZ / "data" / "processed"

_KB: BaseConocimiento | None = None

def _kb() -> BaseConocimiento:
    global _KB
    if _KB is None:
        _KB = BaseConocimiento.desde_corpus()
    return _KB

def get_pm25(estacion: str | None = None, dias: int = 7) -> dict:
    """Devuelve el PM2.5 diario reciente de una estación o el promedio del valle."""
    try:
        df = pd.read_csv(PROCESADOS / "pm25_diario.csv", parse_dates=["dia"])
    except FileNotFoundError:
        return {"error": "No se encontró data/processed/pm25_diario.csv. Ejecuta el pipeline de datos."}

    if estacion:
        coincidencias = df[df["estacion"].str.contains(estacion, case=False, na=False)]
        if coincidencias.empty:
            disponibles = sorted(df["estacion"].unique())[:10]
            return {"error": f"Estación '{estacion}' no encontrada.", "ejemplos_estaciones": disponibles}
        nombre = coincidencias["estacion"].iloc[0]
        serie = (
            coincidencias[coincidencias["estacion"] == nombre]
            .sort_values("dia")
            .tail(dias)[["dia", "pm25", "ica"]]
        )
        registros = [
            {"dia": r.dia.date().isoformat(), "pm25": round(float(r.pm25), 2), "ica": r.ica}
            for r in serie.itertuples()
        ]
        ultimo = registros[-1] if registros else None
        return {"estacion": nombre, "dias": len(registros), "mediciones": registros, "ultimo": ultimo}

    valle = df.groupby("dia").agg(pm25=("pm25", "mean"), pm25_max=("pm25", "max")).reset_index()
    valle = valle.sort_values("dia").tail(dias)
    registros = [
        {"dia": r.dia.date().isoformat(), "pm25_promedio": round(float(r.pm25), 2),
         "pm25_max": round(float(r.pm25_max), 2)}
        for r in valle.itertuples()
    ]
    return {"ambito": "valle (promedio de estaciones)", "dias": len(registros),
            "mediciones": registros, "ultimo": registros[-1] if registros else None}

def predict_tomorrow() -> dict:
    """Predice la categoría ICA del día siguiente con el modelo de la Parte 1."""
    try:
        from src.modelo.predecir import predecir_manana

        return predecir_manana()
    except Exception as e:  # noqa: BLE001
        return {"error": f"No se pudo generar la predicción: {e}"}

def search_docs(consulta: str, k: int = 3) -> dict:
    """Busca en el corpus y devuelve fragmentos con su fuente."""
    try:
        resultados = _kb().buscar(consulta, k=k)
    except Exception as e:  # noqa: BLE001
        return {"error": f"No se pudo buscar en el corpus: {e}"}
    if not resultados:
        return {"consulta": consulta, "resultados": [], "nota": "Sin coincidencias en el corpus."}
    return {
        "consulta": consulta,
        "resultados": [
            {"fuente": r["fuente"], "fragmento": r["texto"], "relevancia": round(r["score"], 4)}
            for r in resultados
        ],
    }

HERRAMIENTAS = {
    "get_pm25": {
        "func": get_pm25,
        "descripcion": "Consulta las mediciones diarias recientes de PM2.5 de una estación o del promedio del valle.",
        "args": {"estacion": "str opcional", "dias": "int opcional (por defecto 7)"},
    },
    "predict_tomorrow": {
        "func": predict_tomorrow,
        "descripcion": "Predice la categoría de calidad del aire (ICA) del día siguiente con el modelo de la Parte 1.",
        "args": {},
    },
    "search_docs": {
        "func": search_docs,
        "descripcion": "Busca en la normativa, los protocolos de episodios y las recomendaciones de salud.",
        "args": {"consulta": "str", "k": "int opcional (por defecto 3)"},
    },
}
