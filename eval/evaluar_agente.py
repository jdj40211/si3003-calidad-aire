"""Evaluación del agente de calidad del aire.

Integrante 3: Juan José Palacio.

Ejecuta las 15 preguntas de eval/preguntas.json contra el agente y verifica, por cada una:
  - que haya usado las herramientas esperadas,
  - que la respuesta contenga las palabras clave esperadas,
  - que cite una fuente del corpus cuando se espera (manejo de citas),
  - que no haya quedado vacía ni con error (manejo de errores).

Escribe un reporte en eval/resultados.md y un resumen en JSON. Uso:
    python -m eval.evaluar_agente            # agente con LLM (si hay clave) y por reglas
    python -m eval.evaluar_agente --solo-llm
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.agente.agente import AgenteCalidadAire  # noqa: E402

PREGUNTAS = RAIZ / "eval" / "preguntas.json"
RESULTADOS_MD = RAIZ / "eval" / "resultados.md"
RESULTADOS_JSON = RAIZ / "eval" / "resultados.json"

def evaluar_caso(agente: AgenteCalidadAire, caso: dict) -> dict:
    traza = agente.responder(caso["pregunta"])
    respuesta = traza.respuesta
    resp_lower = respuesta.lower()

    herramientas_ok = all(h in traza.herramientas_usadas for h in caso["herramientas_esperadas"])
    claves_encontradas = [k for k in caso["palabras_clave"] if k.lower() in resp_lower]
    claves_ok = len(claves_encontradas) >= 1
    cita_ok = (not caso["espera_cita"]) or bool(traza.fuentes)
    sin_error = bool(respuesta.strip()) and "no pude completar" not in resp_lower

    aprueba = herramientas_ok and claves_ok and cita_ok and sin_error
    return {
        "id": caso["id"],
        "pregunta": caso["pregunta"],
        "categoria": caso["categoria"],
        "respuesta": respuesta,
        "herramientas_usadas": traza.herramientas_usadas,
        "herramientas_esperadas": caso["herramientas_esperadas"],
        "fuentes": traza.fuentes,
        "claves_encontradas": claves_encontradas,
        "checks": {
            "herramientas_ok": herramientas_ok,
            "claves_ok": claves_ok,
            "cita_ok": cita_ok,
            "sin_error": sin_error,
        },
        "aprueba": aprueba,
    }

def correr(banco: dict, usar_llm: bool) -> tuple[str, list[dict]]:
    agente = AgenteCalidadAire(usar_llm=usar_llm)
    etiqueta = f"LLM ({agente.config['modelo']})" if agente.modo == "llm" else "Reglas (respaldo)"
    resultados = []
    for c in banco["preguntas"]:
        r = evaluar_caso(agente, c)
        print(f"  [{etiqueta}] {r['id']:>2} {'APRUEBA' if r['aprueba'] else 'REVISAR'}  {r['herramientas_usadas']}")
        resultados.append(r)
    return etiqueta, resultados


def main() -> int:
    banco = json.loads(PREGUNTAS.read_text(encoding="utf-8"))
    corridas = [correr(banco, usar_llm=True)]
    if "--solo-llm" not in sys.argv and corridas[0][0].startswith("LLM"):
        corridas.append(correr(banco, usar_llm=False))
    etiqueta, resultados = corridas[0]
    aprobados = sum(r["aprueba"] for r in resultados)
    total = len(resultados)
    tasa = round(100 * aprobados / total, 1) if total else 0.0

    lineas = [
        "# Resultados de la evaluación del agente",
        "",
        "Integrante 3: Juan José Palacio. Comparación con el agente LLM: Juan David Sierra.",
        "",
        f"**Agente evaluado:** {etiqueta}",
        "",
        f"**Preguntas:** {total} · **Aprobadas:** {aprobados} · **Tasa de acierto:** {tasa}%",
        "",
        "Cada caso se considera aprobado si el agente usó las herramientas esperadas, incluyó al "
        "menos una palabra clave relevante, citó una fuente cuando correspondía y no devolvió error.",
        "",
        "| # | Categoría | Herramientas | Cita | Claves | Resultado |",
        "|---|---|---|---|---|---|",
    ]
    for r in resultados:
        c = r["checks"]
        lineas.append(
            f"| {r['id']} | {r['categoria']} | {'✓' if c['herramientas_ok'] else '✗'} "
            f"| {'✓' if c['cita_ok'] else '✗'} | {'✓' if c['claves_ok'] else '✗'} "
            f"| {'APRUEBA' if r['aprueba'] else 'REVISAR'} |"
        )
    if len(corridas) > 1:
        lineas += ["", "## Comparación de agentes", "",
                   "| Agente | Aprobadas | Herramienta correcta | Cita cuando se espera | Palabras clave |",
                   "|---|---|---|---|---|"]
        for et, rs in corridas:
            n = len(rs)
            def cuenta(clave, rs=rs):
                return sum(r["checks"][clave] for r in rs)
            lineas.append(f"| {et} | {sum(r['aprueba'] for r in rs)}/{n} | {cuenta('herramientas_ok')}/{n} "
                          f"| {cuenta('cita_ok')}/{n} | {cuenta('claves_ok')}/{n} |")
    lineas += ["", "## Notas de rigor", "",
               "- El LLM no responde exactamente igual en cada corrida (temperatura 0,1): entre corridas "
               "el agente LLM obtuvo 13, 14 y 15 de 15. La tabla de arriba es la de la última corrida.",
               "- Las palabras clave de las preguntas 1, 5 y 10 se corrigieron porque se escribieron para un "
               "corpus anterior sin fuentes: la 1 esperaba '37', pero según la Resolución 2254 de 2017 la "
               "categoría dañina para grupos sensibles empieza en 38 µg/m³; la 5 y la 10 esperaban 'interior', "
               "que el POECA no menciona. El motivo de cada cambio está en el campo 'nota' de preguntas.json.",
               "- La pregunta 13 (tipo de mascarilla) no tiene respuesta en el corpus: se espera que el agente "
               "lo diga en lugar de inventar.",
               "- Revisión manual de fidelidad: en una versión anterior del prompt el LLM citaba documentos para "
               "afirmaciones que no estaban en el fragmento (por ejemplo, 'al hacer ejercicio se respira más "
               "profundo' citado a la Resolución 2254). Se corrigió exigiendo que la cita solo acompañe lo que "
               "el fragmento dice y que el conocimiento general vaya sin cita, introducido con 'En general'."]
    lineas += ["", "## Detalle de cada pregunta", ""]
    for r in resultados:
        lineas += [
            f"### {r['id']}. {r['pregunta']}",
            f"- **Herramientas usadas:** {', '.join(r['herramientas_usadas']) or '—'} "
            f"(esperadas: {', '.join(r['herramientas_esperadas'])})",
            f"- **Fuentes citadas:** {', '.join(r['fuentes']) or '—'}",
            f"- **Respuesta:** {r['respuesta']}",
            "",
        ]
    RESULTADOS_MD.write_text("\n".join(lineas), encoding="utf-8")

    resumen = {"agente": etiqueta, "total": total, "aprobados": aprobados, "tasa_acierto": tasa,
               "casos": resultados,
               "comparacion": [{"agente": et, "aprobados": sum(r["aprueba"] for r in rs), "total": len(rs)}
                               for et, rs in corridas]}
    RESULTADOS_JSON.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Evaluación: {aprobados}/{total} aprobadas ({tasa}%).")
    print(f"Reporte: {RESULTADOS_MD.relative_to(RAIZ)}")
    return 0 if aprobados == total else 1

if __name__ == "__main__":
    raise SystemExit(main())
