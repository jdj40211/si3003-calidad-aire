"""Evaluación del agente de calidad del aire.

Integrante 3: Juan José Palacio.

Ejecuta las 15 preguntas de eval/preguntas.json contra el agente y verifica, por cada una:
  - que haya usado las herramientas esperadas,
  - que la respuesta contenga las palabras clave esperadas,
  - que cite una fuente del corpus cuando se espera (manejo de citas),
  - que no haya quedado vacía ni con error (manejo de errores).

Escribe un reporte en eval/resultados.md y un resumen en JSON. Uso:
    python -m eval.evaluar_agente
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

def main() -> int:
    banco = json.loads(PREGUNTAS.read_text(encoding="utf-8"))
    agente = AgenteCalidadAire()

    resultados = [evaluar_caso(agente, c) for c in banco["preguntas"]]
    aprobados = sum(r["aprueba"] for r in resultados)
    total = len(resultados)
    tasa = round(100 * aprobados / total, 1) if total else 0.0

    lineas = [
        "# Resultados de la evaluación del agente",
        "",
        "Integrante 3: Juan José Palacio.",
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

    resumen = {"total": total, "aprobados": aprobados, "tasa_acierto": tasa, "casos": resultados}
    RESULTADOS_JSON.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Evaluación: {aprobados}/{total} aprobadas ({tasa}%).")
    print(f"Reporte: {RESULTADOS_MD.relative_to(RAIZ)}")
    return 0 if aprobados == total else 1

if __name__ == "__main__":
    raise SystemExit(main())
