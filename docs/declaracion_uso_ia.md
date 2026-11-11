# Declaración de uso de IA generativa

**SI3003 Inteligencia Artificial — Universidad EAFIT, 2026-2**
**Equipo:** Juan David Sierra · Keita Ashizawa · Juan José Palacio

En este proyecto usamos herramientas de IA generativa como apoyo al desarrollo. Declaramos su uso de forma transparente:

## Dónde se usó

- **Asistente de código (IA generativa).** Se usó para acelerar la escritura de los módulos del proyecto: estructura del pipeline de datos, el modelo de la Parte 1, el agente con sus herramientas y el RAG, el dashboard en Streamlit y los scripts de evaluación. También para redactar borradores de la documentación (este informe, el README y el corpus del RAG a partir de la normativa y los protocolos oficiales).
- **Claude Code (Anthropic), en la parte de Juan David Sierra.** Se usó como asistente para: verificar el acceso a los datos de datos.gov.co y diagnosticar el problema de escala de la fuente; reparar los archivos que se dañaron al subirlos (cadenas partidas); buscar y extraer el texto de la Resolución 2254 de 2017, el Acuerdo Metropolitano 15 de 2016 (POECA), el reporte del SIATA y la nota de la OMS; escribir el RAG híbrido (embeddings, FAISS y RRF), el loop del agente LLM y la comparación LLM contra reglas en la evaluación; y redactar el README y las secciones del informe sobre el agente.
- **LLM dentro del sistema.** El agente de la Parte 2 usa un modelo de lenguaje con *tool calling* (por defecto `nvidia/nemotron-3.5-super-vl-120b-a12b` en NVIDIA NIM) para decidir qué herramienta llamar y redactar la respuesta con citas. Sin clave de API, responde un agente de respaldo por reglas.

## Cómo se validó

- Todo el código generado con apoyo de IA fue **revisado y probado por el equipo**. El modelo se evalúa contra una línea base de persistencia con una partición temporal; el agente se evalúa con un banco de 15 preguntas (`eval/`) que verifica herramientas, citas y manejo de errores.
- El corpus del RAG se escribió a partir del texto oficial de cada fuente, y ese texto extraído queda en `docs/fuentes/` para verificarlo.

## Errores de la IA que detectamos y corregimos

- Una primera versión del corpus, escrita con ayuda de IA sin consultar los documentos, tenía niveles del protocolo distintos a los del POECA real. Se reemplazó por contenido tomado de las fuentes oficiales.
- Al escribir el documento de la OMS, el asistente agregó una definición del PM2.5 que la nota de la OMS no contiene; se eliminó para no atribuirle a la fuente algo que no dice.
- En la revisión manual de la evaluación, el LLM del agente citaba documentos para afirmaciones que no estaban en el fragmento recuperado. Se corrigió el prompt para que la cita solo acompañe lo que el fragmento dice.
- Las decisiones de diseño (control de calidad de los datos, elección del modelo, arquitectura del agente, vistas del dashboard) fueron tomadas y entendidas por el equipo, no delegadas ciegamente a la herramienta.

## Qué no hizo la IA

- No se usó la IA para inventar datos ni resultados: las métricas provienen de ejecutar el código sobre los datos reales del AMVA.
- El sistema entregado es una herramienta académica y no constituye consejo médico ni reemplaza los avisos oficiales del SIATA ni del AMVA.
