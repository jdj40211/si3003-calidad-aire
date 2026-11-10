"""Limpia las mediciones horarias del AMVA y las agrega por día.

Problema de calidad encontrado en la fuente (g4t8-zkc3): entre 2020 y 2023
muchas estaciones publican PM2.5, viento y lluvia en una escala distinta
(valores multiplicados por 10 o 100, sin un factor constante). No se corrige
ningún valor: se descartan los meses de cada estación cuya distribución no es
físicamente plausible. Las reglas están en REGLAS_MES y el reporte de cuánto se
conserva queda en data/processed/calidad_datos.csv.

Uso:
    python -m src.datos.procesar
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CRUDOS = RAIZ / "data" / "raw"
PROCESADOS = RAIZ / "data" / "processed"

# Un mes de una estación se conserva solo si su mediana y su percentil 99
# horarios quedan por debajo de estos topes.
REGLAS_MES = {
    "PM25": {"mediana": 60.0, "p99": 300.0},     # µg/m³
    "VViento": {"mediana": 8.0, "p99": 20.0},    # m/s
    "PLiquida": {"mediana": 1.0, "p99": 15.0},   # mm en una hora
    "TAire2": {"mediana": 35.0, "p99": 40.0},    # °C
}
# Valor horario máximo aceptado dentro de un mes válido.
TOPE_HORARIO = {"PM25": 500.0, "VViento": 30.0, "PLiquida": 100.0, "TAire2": 45.0}
# Valor horario mínimo aceptado (una temperatura de 0 °C en el valle es un sensor caído).
MINIMO_HORARIO = {"PM25": 0.0, "VViento": 0.0, "PLiquida": 0.0, "TAire2": 5.0}
# Horas mínimas con dato para que un promedio diario cuente (75 % del día).
HORAS_MIN = 18

# Categorías del Índice de Calidad del Aire para PM2.5 (Resolución 2254 de 2017,
# promedio de 24 h). Se agrupan en tres clases para el modelo.
CORTES_ICA = [0, 12.5, 37.5, 55.5, 150.5, 250.5, float("inf")]
NOMBRES_ICA = ["Buena", "Aceptable", "Dañina sensibles", "Dañina", "Muy dañina", "Peligrosa"]


def categoria_ica(pm25: float) -> str:
    return pd.cut([pm25], CORTES_ICA, labels=NOMBRES_ICA, right=False)[0]


def clase_modelo(pm25: float) -> int:
    """0 = Buena, 1 = Aceptable, 2 = Dañina para grupos sensibles o peor."""
    if pm25 < 12.5:
        return 0
    if pm25 < 37.5:
        return 1
    return 2


def cargar(variable: str) -> pd.DataFrame:
    d = pd.read_csv(CRUDOS / f"amva_{variable}_horario.csv", parse_dates=["fecha"])
    d["mes"] = d["fecha"].dt.to_period("M")
    return d


def filtrar_meses(d: pd.DataFrame, variable: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    regla = REGLAS_MES[variable]
    stats = d.groupby(["estacion", "mes"])["valor"].agg(
        mediana="median", p99=lambda x: x.quantile(0.99), horas="count"
    ).reset_index()
    stats["valido"] = (stats["mediana"] <= regla["mediana"]) & (stats["p99"] <= regla["p99"])
    validos = stats.loc[stats["valido"], ["estacion", "mes"]]
    limpio = d.merge(validos, on=["estacion", "mes"])
    limpio = limpio[(limpio["valor"] >= MINIMO_HORARIO[variable]) & (limpio["valor"] <= TOPE_HORARIO[variable])]
    stats["variable"] = variable
    return limpio, stats


def diario(d: pd.DataFrame, agregacion: str) -> pd.DataFrame:
    d = d.assign(dia=d["fecha"].dt.normalize())
    g = d.groupby(["estacion", "dia"])["valor"]
    out = g.agg(valor=agregacion, horas="count").reset_index()
    return out[out["horas"] >= HORAS_MIN]


def main() -> None:
    PROCESADOS.mkdir(parents=True, exist_ok=True)
    reporte = []

    pm = cargar("PM25")
    estaciones = (
        pm.groupby("estacion")[["municipio", "latitud", "longitud"]].first().reset_index()
    )
    pm_limpio, st = filtrar_meses(pm, "PM25")
    reporte.append(st)
    pm_dia = diario(pm_limpio, "mean").rename(columns={"valor": "pm25"})
    pm_dia["pm25"] = pm_dia["pm25"].round(2)
    pm_dia["ica"] = pm_dia["pm25"].map(categoria_ica)
    pm_dia["clase"] = pm_dia["pm25"].map(clase_modelo)
    pm_dia = pm_dia.merge(estaciones, on="estacion")
    pm_dia.to_csv(PROCESADOS / "pm25_diario.csv", index=False)

    # Meteorología: promedio del valle (media entre estaciones válidas de cada día).
    meteo = []
    for variable, agregacion, nombre in [
        ("PLiquida", "sum", "lluvia_mm"),
        ("VViento", "mean", "viento_ms"),
        ("TAire2", "mean", "temp_c"),
    ]:
        d = cargar(variable)
        limpio, st = filtrar_meses(d, variable)
        reporte.append(st)
        dd = diario(limpio, agregacion)
        meteo.append(dd.groupby("dia")["valor"].mean().round(2).rename(nombre))
    pd.concat(meteo, axis=1, sort=True).reset_index().to_csv(PROCESADOS / "meteo_diario.csv", index=False)

    estaciones.to_csv(PROCESADOS / "estaciones.csv", index=False)
    rep = pd.concat(reporte)
    resumen = rep.groupby("variable").agg(
        meses=("valido", "size"), meses_validos=("valido", "sum"),
        horas=("horas", "sum"),
    )
    resumen["pct_meses_validos"] = (100 * resumen["meses_validos"] / resumen["meses"]).round(1)
    resumen.to_csv(PROCESADOS / "calidad_datos.csv")
    print(resumen)
    print(f"\nPM2.5 diario: {len(pm_dia):,} estación-días, {pm_dia['estacion'].nunique()} estaciones,"
          f" {pm_dia['dia'].min().date()} a {pm_dia['dia'].max().date()}")
    print(pm_dia["ica"].value_counts().to_string())


if __name__ == "__main__":
    main()
