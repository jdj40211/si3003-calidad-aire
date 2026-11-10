"""Construcción del dataset diario del Valle de Aburrá con ingeniería de características.

Replica, como código reutilizable, el preprocesamiento del notebook de la Parte 1
(`notebooks/Prediccion_PM25_ICA_Valle_de_Aburra.ipynb`) para que tanto el modelo
como el dashboard y el agente usen exactamente las mismas columnas.

El objetivo (`target_clase_next_day`) es la clase ICA más crítica del día siguiente:
    0 = Buena, 1 = Aceptable, 2 = Dañina para grupos sensibles o peor.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROCESADOS = RAIZ / "data" / "processed"

FEATURES = [
    "pm25_mean", "pm25_max", "lluvia_mm", "viento_ms", "temp_c",
    "pm25_mean_lag_1", "pm25_max_lag_1", "pm25_mean_lag_2", "pm25_max_lag_2",
    "pm25_mean_lag_3", "pm25_max_lag_3", "pm25_rolling_mean_3d", "pm25_rolling_max_3d",
    "month", "dayofweek", "is_weekend", "is_critical_season",
]

NOMBRES_CLASE = {0: "Buena", 1: "Aceptable", 2: "Dañina para grupos sensibles o peor"}

def cargar_diario_valle(
    pm25_csv: Path | None = None, meteo_csv: Path | None = None
) -> pd.DataFrame:
    """Agrega el PM2.5 por día a nivel de todo el valle y lo cruza con la meteorología."""
    pm25_csv = pm25_csv or PROCESADOS / "pm25_diario.csv"
    meteo_csv = meteo_csv or PROCESADOS / "meteo_diario.csv"

    df_pm = pd.read_csv(pm25_csv, parse_dates=["dia"])
    df_met = pd.read_csv(meteo_csv, parse_dates=["dia"])

    diario = (
        df_pm.groupby("dia")
        .agg(pm25_mean=("pm25", "mean"), pm25_max=("pm25", "max"), ica_max=("clase", "max"))
        .reset_index()
    )
    df = pd.merge(diario, df_met, on="dia", how="left").sort_values("dia").reset_index(drop=True)

    df["lluvia_mm"] = df["lluvia_mm"].fillna(0)
    df["viento_ms"] = df["viento_ms"].interpolate(method="linear").bfill().ffill()
    df["temp_c"] = df["temp_c"].interpolate(method="linear").bfill().ffill()
    return df

def construir_caracteristicas(df_diario: pd.DataFrame, con_objetivo: bool = True) -> pd.DataFrame:
    """Agrega lags, medias móviles y variables de calendario."""
    df = df_diario.sort_values("dia").reset_index(drop=True).copy()

    for lag in (1, 2, 3):
        df[f"pm25_mean_lag_{lag}"] = df["pm25_mean"].shift(lag)
        df[f"pm25_max_lag_{lag}"] = df["pm25_max"].shift(lag)

    df["pm25_rolling_mean_3d"] = df["pm25_mean"].shift(1).rolling(window=3).mean()
    df["pm25_rolling_max_3d"] = df["pm25_max"].shift(1).rolling(window=3).max()

    df["month"] = df["dia"].dt.month
    df["dayofweek"] = df["dia"].dt.dayofweek
    df["is_weekend"] = df["dayofweek"].isin([5, 6]).astype(int)
    df["is_critical_season"] = df["month"].isin([3, 4, 10, 11]).astype(int)

    if con_objetivo:
        df["target_clase_next_day"] = df["ica_max"].shift(-1)
        df = df.dropna().reset_index(drop=True)
    else:
        df = df.dropna(subset=FEATURES).reset_index(drop=True)
    return df

def dataset_entrenamiento(
    pm25_csv: Path | None = None, meteo_csv: Path | None = None
) -> pd.DataFrame:
    """Atajo: datos diarios + características + objetivo, listo para entrenar."""
    return construir_caracteristicas(cargar_diario_valle(pm25_csv, meteo_csv), con_objetivo=True)
