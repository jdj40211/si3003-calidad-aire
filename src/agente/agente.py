"""Loop del agente de calidad del aire con tool calling y RAG.

El agente responde preguntas sobre el PM2.5 del Valle de Aburrá. En cada turno decide
qué herramientas usar (get_pm25, predict_tomorrow, search_docs), las ejecuta, reúne
evidencia y redacta una respuesta citando las fuentes del corpus. El loop está acotado
por T_max iteraciones para no ciclar indefinidamente.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .herramientas import HERRAMIENTAS

T_MAX = 4  # máximo de iteraciones del loop de razonamiento-acción

@dataclass
class Traza:
    """Registro de lo que hizo el agente en una pregunta: útil para depurar y evaluar."""
    pregunta: str
    pasos: list[dict] = field(default_factory=list)
    respuesta: str = ""
    fuentes: list[str] = field(default_factory=list)
    herramientas_usadas: list[str] = field(default_factory=list)

def _planificar_por_reglas(pregunta: str, ya_usadas: set[str]) -> list[dict]:
    """Decide qué herramientas llamar según palabras clave; no repite las ya usadas."""
    q = pregunta.lower()
    plan: list[dict] = []

    pide_prediccion = any(p in q for p in ["mañana", "manana", "predic", "pronóst", "pronost", "futuro", "siguiente"])
    pide_actual = any(p in q for p in ["hoy", "actual", "ahora", "último", "ultimo", "reciente", "cómo está", "como esta", "pm2", "medición", "medicion", "nivel"])
    pide_docs = any(p in q for p in ["norma", "resolución", "resolucion", "protocolo", "alerta", "recomend", "salud", "qué significa", "que significa", "categoría", "categoria", "ica", "episodio", "sensible", "deporte", "ejercicio", "salir", "mascarilla"])

    estacion = None
    m = re.search(r"estaci[oó]n\s+(?:de\s+)?([A-Za-zÁÉÍÓÚÑáéíóúñ0-9 ]{3,40})", pregunta)
    if m:
        estacion = m.group(1).strip().rstrip(".?!")
        for sobrante in (" hoy", " ahora", " actual", " reciente", " ayer"):
            if estacion.lower().endswith(sobrante):
                estacion = estacion[: -len(sobrante)].strip()

    if pide_prediccion and "predict_tomorrow" not in ya_usadas:
        plan.append({"herramienta": "predict_tomorrow", "args": {}})
    if (pide_actual or estacion) and "get_pm25" not in ya_usadas:
        args = {"estacion": estacion} if estacion else {}
        plan.append({"herramienta": "get_pm25", "args": args})
    if pide_docs and "search_docs" not in ya_usadas:
        plan.append({"herramienta": "search_docs", "args": {"consulta": pregunta}})

    if not plan and "search_docs" not in ya_usadas:
        plan.append({"herramienta": "search_docs", "args": {"consulta": pregunta}})
    return plan

def _redactar(pregunta: str, evidencia: list[dict]) -> tuple[str, list[str]]:
    """Convierte la evidencia recogida en una respuesta en lenguaje natural con citas."""
    partes: list[str] = []
    fuentes: list[str] = []

    for ev in evidencia:
        herr, res = ev["herramienta"], ev["resultado"]
        if "error" in res:
            partes.append(f"No pude completar «{herr}»: {res['error']}")
            continue

        if herr == "get_pm25":
            ultimo = res.get("ultimo")
            if ultimo and "pm25" in ultimo:
                partes.append(
                    f"La última medición de la estación {res['estacion']} fue "
                    f"{ultimo['pm25']} µg/m³ ({ultimo['ica']}) el {ultimo['dia']}."
                )
            elif ultimo:
                partes.append(
                    f"El promedio del valle más reciente ({ultimo['dia']}) fue "
                    f"{ultimo['pm25_promedio']} µg/m³, con un máximo por estación de "
                    f"{ultimo['pm25_max']} µg/m³."
                )
        elif herr == "predict_tomorrow":
            partes.append(
                f"Para el día siguiente al {res['fecha_base']}, el modelo prevé una categoría "
                f"«{res['categoria_predicha']}» (PM2.5 de hoy: {res['pm25_mean_hoy']} µg/m³ en promedio)."
            )
        elif herr == "search_docs":
            for r in res.get("resultados", []):
                fragmento = r["fragmento"].replace("
", " ").strip()
                if len(fragmento) > 320:
                    fragmento = fragmento[:317] + "..."
                partes.append(f"Según {r['fuente']}: {fragmento}")
                if r["fuente"] not in fuentes:
                    fuentes.append(r["fuente"])

    if not partes:
        return ("No encontré información suficiente para responder con los datos y documentos disponibles.", fuentes)

    respuesta = " ".join(partes)
    respuesta += ("

Nota: herramienta académica; no reemplaza el consejo médico ni los avisos "
                  "oficiales del SIATA y el AMVA.")
    if fuentes:
        respuesta += "

Fuentes: " + "; ".join(fuentes)
    return respuesta, fuentes

class AgenteCalidadAire:
    def __init__(self, t_max: int = T_MAX, usar_llm: bool = False):
        self.t_max = t_max
        self.usar_llm = usar_llm

    def _ejecutar_herramienta(self, nombre: str, args: dict) -> dict:
        spec = HERRAMIENTAS.get(nombre)
        if spec is None:
            return {"error": f"Herramienta desconocida: {nombre}"}
        try:
            return spec["func"](**args)
        except TypeError as e:
            return {"error": f"Argumentos inválidos para {nombre}: {e}"}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Fallo al ejecutar {nombre}: {e}"}

    def responder(self, pregunta: str) -> Traza:
        """Ejecuta el loop acotado y devuelve una Traza con respuesta, fuentes y pasos."""
        traza = Traza(pregunta=pregunta)
        evidencia: list[dict] = []
        usadas: set[str] = set()

        for iteracion in range(self.t_max):
            plan = _planificar_por_reglas(pregunta, usadas)
            if not plan:
                break
            for accion in plan:
                nombre, args = accion["herramienta"], accion["args"]
                resultado = self._ejecutar_herramienta(nombre, args)
                usadas.add(nombre)
                evidencia.append({"herramienta": nombre, "resultado": resultado})
                traza.pasos.append({"iteracion": iteracion, "herramienta": nombre,
                                    "args": args, "resultado": resultado})
            break

        respuesta, fuentes = _redactar(pregunta, evidencia)
        traza.respuesta = respuesta
        traza.fuentes = fuentes
        traza.herramientas_usadas = sorted(usadas)
        return traza

def responder(pregunta: str, t_max: int = T_MAX) -> str:
    """Atajo para una respuesta en texto plano (lo que usa el chat del dashboard)."""
    return AgenteCalidadAire(t_max=t_max).responder(pregunta).respuesta

if __name__ == "__main__":
    import sys

    agente = AgenteCalidadAire()
    preguntas = sys.argv[1:] or ["¿Qué significa la categoría dañina para grupos sensibles?"]
    for p in preguntas:
        t = agente.responder(p)
        print(f"
P: {p}
R: {t.respuesta}
Herramientas: {t.herramientas_usadas}")
