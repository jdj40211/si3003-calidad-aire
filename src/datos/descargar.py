"""Descarga las mediciones horarias de las estaciones del AMVA desde datos.gov.co.

Fuente: "Calidad del Aire en Colombia" (SISAIRE, IDEAM), identificador g4t8-zkc3.
https://www.datos.gov.co/resource/g4t8-zkc3

Uso:
    python -m src.datos.descargar            # todas las variables
    python -m src.datos.descargar PM2.5      # solo una variable

Escribe un CSV por variable en data/raw/ con las columnas
estacion, municipio, latitud, longitud, fecha, valor.
"""
import csv
import io
import sys
import time
from pathlib import Path

import requests

URL = "https://www.datos.gov.co/resource/g4t8-zkc3.csv"
AUTORIDAD = "AMVA"
VARIABLES = ["PM2.5", "PLiquida", "VViento", "TAire2"]
PAGINA = 50_000
RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "data" / "raw"


def descargar_variable(variable: str) -> Path:
    """Baja todas las filas de una variable, por páginas, y las guarda en un CSV."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"amva_{variable.replace('.', '')}_horario.csv"
    columnas = "nombre_est,municipio,latitud,longitud,med_fecha_inicio,med_concentracion_estandar"
    # duraci_n=60: solo mediciones horarias. Dos estaciones también publican
    # muestras manuales de 24 h (duraci_n=1440) que no se deben mezclar.
    filtro = f"nombre_fgda='{AUTORIDAD}' AND msfl_code='{variable}' AND duraci_n=60"
    total = 0
    with destino.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["estacion", "municipio", "latitud", "longitud", "fecha", "valor"])
        desde = 0
        while True:
            params = {
                "$select": columnas,
                "$where": filtro,
                "$order": ":id",
                "$limit": PAGINA,
                "$offset": desde,
            }
            for intento in range(5):
                try:
                    r = requests.get(URL, params=params, timeout=120)
                    r.raise_for_status()
                    break
                except requests.RequestException as e:
                    espera = 5 * (intento + 1)
                    print(f"  error ({e}); reintento en {espera} s", file=sys.stderr)
                    time.sleep(espera)
            else:
                raise RuntimeError(f"No se pudo descargar {variable} desde la fila {desde}")
            filas = list(csv.reader(io.StringIO(r.text)))[1:]
            if not filas:
                break
            escritor.writerows(filas)
            total += len(filas)
            desde += PAGINA
            print(f"  {variable}: {total:,} filas")
    print(f"{variable}: {total:,} filas en {destino.relative_to(RAIZ)}")
    return destino


if __name__ == "__main__":
    for v in sys.argv[1:] or VARIABLES:
        descargar_variable(v)
