"""Entrena, evalúa, guarda y carga el clasificador de la categoría ICA del día siguiente.

Random Forest balanceado comparado contra la línea base de persistencia (mañana = hoy),
con una división temporal (sin barajar) que respeta el orden de las fechas.

Uso:
    python -m src.modelo.predecir            # entrena, evalúa y guarda el modelo
    python -m src.modelo.predecir --eval     # solo imprime las métricas
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

from .caracteristicas import (
    FEATURES,
    NOMBRES_CLASE,
    cargar_diario_valle,
    construir_caracteristicas,
    dataset_entrenamiento,
)

RAIZ = Path(__file__).resolve().parents[2]
MODELO_PATH = RAIZ / "data" / "processed" / "modelo_rf.joblib"
METRICAS_PATH = RAIZ / "eval" / "metricas_modelo.json"

def entrenar(df: pd.DataFrame | None = None, test_size: float = 0.2):
    """Entrena el Random Forest balanceado y devuelve (modelo, métricas)."""
    df = dataset_entrenamiento() if df is None else df
    X = df[FEATURES]
    y = df["target_clase_next_day"].astype(int)

    corte = int(len(df) * (1 - test_size))
    X_train, X_test = X.iloc[:corte], X.iloc[corte:]
    y_train, y_test = y.iloc[:corte], y.iloc[corte:]

    modelo = RandomForestClassifier(
        n_estimators=200, max_depth=10, class_weight="balanced", random_state=42
    )
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)
    y_base = df.iloc[corte:]["ica_max"].astype(int)

    metricas = {
        "n_entrenamiento": int(len(X_train)),
        "n_prueba": int(len(X_test)),
        "accuracy_modelo": round(float(accuracy_score(y_test, y_pred)), 4),
        "accuracy_baseline": round(float(accuracy_score(y_test, y_base)), 4),
        "f1_macro_modelo": round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro_baseline": round(float(f1_score(y_test, y_base, average="macro", zero_division=0)), 4),
        "f1_weighted_modelo": round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
    }
    metricas["mejora_accuracy_vs_baseline"] = round(
        metricas["accuracy_modelo"] - metricas["accuracy_baseline"], 4
    )
    return modelo, metricas

def guardar(modelo, metricas: dict) -> None:
    import joblib

    MODELO_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": modelo, "features": FEATURES}, MODELO_PATH)
    METRICAS_PATH.write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")

def cargar_o_entrenar():
    """Devuelve (modelo, features). Entrena y guarda si no hay un modelo en disco."""
    if MODELO_PATH.exists():
        import joblib

        bundle = joblib.load(MODELO_PATH)
        return bundle["modelo"], bundle["features"]
    modelo, metricas = entrenar()
    guardar(modelo, metricas)
    return modelo, FEATURES

def predecir_manana(
    pm25_csv: Path | None = None, meteo_csv: Path | None = None
) -> dict:
    """Predice la categoría ICA del día siguiente a partir del último día disponible."""
    modelo, features = cargar_o_entrenar()
    df_diario = cargar_diario_valle(pm25_csv, meteo_csv)
    df_feat = construir_caracteristicas(df_diario, con_objetivo=False)
    if df_feat.empty:
        raise ValueError("No hay suficientes días consecutivos para construir las características.")

    ultima = df_feat.iloc[[-1]]
    X = ultima[features]
    clase = int(modelo.predict(X)[0])
    proba = modelo.predict_proba(X)[0]
    clases_modelo = list(modelo.classes_)
    probabilidades = {
        NOMBRES_CLASE[int(c)]: round(float(p), 4) for c, p in zip(clases_modelo, proba)
    }
    return {
        "fecha_base": ultima["dia"].iloc[0].date().isoformat(),
        "clase_predicha": clase,
        "categoria_predicha": NOMBRES_CLASE[clase],
        "pm25_mean_hoy": round(float(ultima["pm25_mean"].iloc[0]), 2),
        "pm25_max_hoy": round(float(ultima["pm25_max"].iloc[0]), 2),
        "probabilidades": probabilidades,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Modelo de categoría ICA del día siguiente.")
    parser.add_argument("--eval", action="store_true", help="Solo imprimir métricas sin guardar.")
    args = parser.parse_args()

    modelo, metricas = entrenar()
    if not args.eval:
        guardar(modelo, metricas)
        print("Modelo guardado en:", MODELO_PATH.relative_to(RAIZ))
    print(json.dumps(metricas, ensure_ascii=False, indent=2))

    pred = predecir_manana()
    print("Prediccion para el dia siguiente al ultimo dato:")
    print(json.dumps(pred, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
