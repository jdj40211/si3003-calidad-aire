"""Agente de calidad del aire: loop de un LLM con tool calling y RAG.

En cada iteración el LLM decide si llama una herramienta (get_pm25,
predict_tomorrow, search_docs) o si ya puede responder. Los resultados de las
herramientas, incluidos los errores, vuelven al LLM como observación. El loop está
acotado por T_MAX iteraciones; si se agotan, se pide una respuesta final sin más
herramientas.

El LLM se usa por medio del SDK de OpenAI contra un endpoint compatible (NVIDIA NIM
por defecto; Groq u otro con LLM_BASE_URL). Sin clave de API, o si el proveedor falla,
el agente usa el planificador por reglas de este mismo archivo como respaldo, para
que el dashboard nunca se quede sin responder.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .herramientas import HERRAMIENTAS

T_MAX = 5  # máximo de iteraciones del loop de razonamiento-acción

@dataclass
class Traza:
    """Registro de lo que hizo el agente en una pregunta: útil para depurar y evaluar."""
    pregunta: str
    pasos: list[dict] = field(default_factory=list)
    respuesta: str = ""
    fuentes: list[str] = field(default_factory=list)
    herramientas_usadas: list[str] = field(default_factory=list)
    modo: str = "reglas"         # "llm" o "reglas"
    modelo: str = ""
    nota: str = ""               # por qué se usó el respaldo, si aplica

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
                fragmento = r["fragmento"].replace("\n", " ").strip()
                if len(fragmento) > 320:
                    fragmento = fragmento[:317] + "..."
                partes.append(f"Según {r['fuente']}: {fragmento}")
                if r["fuente"] not in fuentes:
                    fuentes.append(r["fuente"])

    if not partes:
        return ("No encontré información suficiente para responder con los datos y documentos disponibles.", fuentes)

    respuesta = " ".join(partes)
    respuesta += ("\n\nNota: herramienta académica; no reemplaza el consejo médico ni los avisos "
                  "oficiales del SIATA y el AMVA.")
    if fuentes:
        respuesta += "\n\nFuentes: " + "; ".join(fuentes)
    return respuesta, fuentes

# ---------------------------------------------------------------------------
# Configuración del LLM
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[2]

PROVEEDORES = {
    "nvidia": {"base_url": "https://integrate.api.nvidia.com/v1", "clave": "NVIDIA_API_KEY",
               "modelo": "nvidia/nemotron-3.5-super-vl-120b-a12b"},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "clave": "GROQ_API_KEY",
             "modelo": "llama-3.3-70b-versatile"},
}

PROMPT_SISTEMA = """Eres un asistente de calidad del aire del Valle de Aburrá (Medellín y su área metropolitana).
Ayudas a ciudadanos a entender el PM2.5 y qué hacer al respecto.

Reglas:
1. Usa las herramientas para obtener datos; no inventes cifras, fechas, normas ni medidas.
   - get_pm25: mediciones diarias de PM2.5 de una estación o del promedio del valle.
   - predict_tomorrow: categoría de calidad del aire prevista para el día siguiente (modelo propio).
   - search_docs: normativa (Resolución 2254 de 2017), protocolo POECA del Área Metropolitana,
     reporte del SIATA y documentación de los datos y el modelo del proyecto.
2. Para cualquier pregunta sobre normas, categorías, efectos en la salud, medidas o recomendaciones,
   llama search_docs antes de responder.
3. Cita cada dato tomado de search_docs con el campo "cita" del resultado, entre paréntesis,
   por ejemplo: (Fuente: Resolución 2254 de 2017..., Niveles de prevención...).
   Las mediciones de get_pm25 se citan como (Datos: SISAIRE-IDEAM, estación <nombre>, <fecha>)
   y la predicción como (Modelo del proyecto). No atribuyas a una norma un dato que salió de
   get_pm25 o de predict_tomorrow.
4. Si una herramienta devuelve un error, explícalo con claridad y responde con lo que sí sepas.
5. Los datos llegan hasta el 31 de diciembre de 2025: di siempre la fecha de la medición y no
   la presentes como el dato de hoy.
6. Responde en español, en máximo 6 oraciones, claro para cualquier persona.
7. No des consejo médico personalizado: recuerda que es una herramienta académica y remite a los
   avisos oficiales del SIATA y del Área Metropolitana cuando haya riesgo para la salud."""

ESQUEMAS = [
    {"type": "function", "function": {
        "name": "get_pm25",
        "description": "Mediciones diarias recientes de PM2.5 (µg/m³) con su categoría ICA, de una estación del AMVA o del promedio del valle si no se indica estación.",
        "parameters": {"type": "object", "properties": {
            "estacion": {"type": "string", "description": "Nombre o parte del nombre de la estación, por ejemplo 'Altavista' o 'Tráfico Centro'. Omitir para el promedio del valle."},
            "dias": {"type": "integer", "description": "Número de días recientes, entre 1 y 30. Por defecto 7."}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "predict_tomorrow",
        "description": "Predice con el modelo clásico del proyecto la categoría de calidad del aire del día siguiente para el promedio del valle (Buena, Aceptable o Dañina para grupos sensibles o peor), con sus probabilidades.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "search_docs",
        "description": "Busca en el corpus de documentos oficiales: Resolución 2254 de 2017 (límites, niveles de prevención/alerta/emergencia, ICA y efectos en la salud), protocolo POECA del AMVA (niveles y medidas), reporte del SIATA y documentación del proyecto. Devuelve fragmentos con su cita.",
        "parameters": {"type": "object", "properties": {
            "consulta": {"type": "string", "description": "Lo que se quiere encontrar, en lenguaje natural."},
            "k": {"type": "integer", "description": "Número de fragmentos, entre 1 y 5. Por defecto 3."}},
            "required": ["consulta"]}}},
]


def _cargar_entorno() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except ImportError:
        pass


def configuracion_llm() -> dict | None:
    """Proveedor, modelo y clave a partir de variables de entorno, o None si no hay clave."""
    _cargar_entorno()
    nombre = os.getenv("LLM_PROVEEDOR", "").lower()
    if not nombre:
        nombre = next((n for n, p in PROVEEDORES.items() if os.getenv(p["clave"])), "")
    if nombre not in PROVEEDORES:
        return None
    p = PROVEEDORES[nombre]
    clave = os.getenv(p["clave"])
    if not clave:
        return None
    return {"proveedor": nombre, "clave": clave,
            "base_url": os.getenv("LLM_BASE_URL", p["base_url"]),
            "modelo": os.getenv("LLM_MODELO", p["modelo"])}


def _extras_proveedor(modelo: str) -> dict:
    # Parámetro propio de los Nemotron 3 de NVIDIA: sin esto el modelo gasta los tokens
    # razonando y puede devolver content vacío. Se aísla aquí para no enviarlo a otros.
    if "nemotron-3" in modelo:
        return {"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}
    return {}


def _citas(resultado: dict) -> dict:
    """Agrega a cada fragmento de search_docs un campo 'cita' listo para usar."""
    for r in resultado.get("resultados", []):
        r["cita"] = f"{r.get('documento') or r['fuente']}, {r.get('seccion', '')}".strip(", ")
    return resultado


# ---------------------------------------------------------------------------
# Agente
# ---------------------------------------------------------------------------
class AgenteCalidadAire:
    def __init__(self, t_max: int = T_MAX, usar_llm: bool = True):
        self.t_max = t_max
        self.config = configuracion_llm() if usar_llm else None
        self._cliente = None
        if self.config:
            from openai import OpenAI

            self._cliente = OpenAI(base_url=self.config["base_url"], api_key=self.config["clave"],
                                   timeout=60, max_retries=2)

    @property
    def modo(self) -> str:
        return "llm" if self._cliente else "reglas"

    def _ejecutar_herramienta(self, nombre: str, args: dict) -> dict:
        spec = HERRAMIENTAS.get(nombre)
        if spec is None:
            return {"error": f"Herramienta desconocida: {nombre}"}
        try:
            resultado = spec["func"](**args)
        except TypeError as e:
            return {"error": f"Argumentos inválidos para {nombre}: {e}"}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Fallo al ejecutar {nombre}: {e}"}
        return _citas(resultado) if nombre == "search_docs" else resultado

    # --- loop con el LLM ------------------------------------------------------
    def _llamar(self, mensajes: list[dict], con_herramientas: bool):
        kwargs = dict(model=self.config["modelo"], messages=mensajes, temperature=0.1,
                      max_tokens=700, **_extras_proveedor(self.config["modelo"]))
        if con_herramientas:
            kwargs.update(tools=ESQUEMAS, tool_choice="auto")
        return self._cliente.chat.completions.create(**kwargs).choices[0].message

    def _responder_llm(self, pregunta: str, traza: Traza) -> None:
        mensajes: list[dict] = [{"role": "system", "content": PROMPT_SISTEMA},
                                {"role": "user", "content": pregunta}]
        usadas: list[str] = []
        recuperados: list[dict] = []
        vistas: set[str] = set()

        for iteracion in range(self.t_max):
            msg = self._llamar(mensajes, con_herramientas=True)
            if not msg.tool_calls:
                traza.respuesta = (msg.content or "").strip()
                break
            mensajes.append({"role": "assistant", "content": msg.content or "",
                             "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                nombre = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                firma = f"{nombre}:{json.dumps(args, sort_keys=True)}"
                if firma in vistas:
                    resultado = {"error": "Esta llamada ya se hizo con los mismos argumentos; usa el resultado anterior."}
                else:
                    vistas.add(firma)
                    resultado = self._ejecutar_herramienta(nombre, args)
                if nombre not in usadas:
                    usadas.append(nombre)
                recuperados.extend(resultado.get("resultados", []) if nombre == "search_docs" else [])
                traza.pasos.append({"iteracion": iteracion, "herramienta": nombre, "args": args,
                                    "resultado": resultado})
                mensajes.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(resultado, ensure_ascii=False, default=str)[:6000]})
        else:
            # Se agotó T_MAX: se pide la respuesta final con lo que ya se tiene.
            mensajes.append({"role": "user", "content": "Ya no puedes llamar más herramientas. Responde ahora con la información obtenida."})
            traza.respuesta = (self._llamar(mensajes, con_herramientas=False).content or "").strip()
            traza.nota = f"Se alcanzó el máximo de {self.t_max} iteraciones."

        if not traza.respuesta:
            traza.respuesta = "No pude generar una respuesta con la información disponible."
        traza.herramientas_usadas = usadas
        # Fuentes: los documentos recuperados que la respuesta efectivamente cita.
        citadas = []
        for r in recuperados:
            if (r.get("documento") and r["documento"][:25] in traza.respuesta) or r["fuente"] in traza.respuesta \
                    or (r.get("seccion") and r["seccion"][:25] in traza.respuesta):
                if r["fuente"] not in citadas:
                    citadas.append(r["fuente"])
        traza.fuentes = citadas

    # --- respaldo por reglas ----------------------------------------------------
    def _responder_reglas(self, pregunta: str, traza: Traza) -> None:
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
        traza.respuesta, traza.fuentes = _redactar(pregunta, evidencia)
        traza.herramientas_usadas = sorted(usadas)

    def responder(self, pregunta: str) -> Traza:
        """Ejecuta el loop y devuelve una Traza con respuesta, fuentes, herramientas y pasos."""
        traza = Traza(pregunta=pregunta)
        if self._cliente:
            traza.modo, traza.modelo = "llm", self.config["modelo"]
            try:
                self._responder_llm(pregunta, traza)
                return traza
            except Exception as e:  # noqa: BLE001  (red, clave inválida, límite del proveedor)
                traza = Traza(pregunta=pregunta, nota=f"El LLM no respondió ({type(e).__name__}); se usó el agente por reglas.")
        else:
            traza.nota = "Sin clave de LLM configurada; se usó el agente por reglas."
        traza.modo = "reglas"
        self._responder_reglas(pregunta, traza)
        return traza


def responder(pregunta: str, t_max: int = T_MAX) -> str:
    """Atajo para una respuesta en texto plano."""
    return AgenteCalidadAire(t_max=t_max).responder(pregunta).respuesta


if __name__ == "__main__":
    import sys

    agente = AgenteCalidadAire()
    print(f"Modo: {agente.modo}" + (f" ({agente.config['modelo']})" if agente.config else ""))
    preguntas = sys.argv[1:] or ["¿Qué significa la categoría dañina para grupos sensibles?"]
    for p in preguntas:
        t = agente.responder(p)
        print(f"\nP: {p}\nR: {t.respuesta}\nHerramientas: {t.herramientas_usadas} | Fuentes: {t.fuentes} | Modo: {t.modo} {t.nota}")
