# Declaración de uso de IA generativa

**SI3003 Inteligencia Artificial — Universidad EAFIT, 2026-2**
**Equipo:** Juan David Sierra · Keita Ashizawa · Juan José Palacio

En este proyecto usamos herramientas de IA generativa como apoyo al desarrollo. Declaramos su uso de forma transparente:

## Dónde se usó

- **Asistente de código (IA generativa).** Se usó para acelerar la escritura de los módulos del proyecto: estructura del pipeline de datos, el modelo de la Parte 1, el agente con sus herramientas y el RAG, el dashboard en Streamlit y los scripts de evaluación. También para redactar borradores de la documentación (este informe, el README y el corpus del RAG a partir de la normativa y los protocolos oficiales).
- **Agente del propio sistema.** El componente de IA moderna del proyecto (Parte 2) usa recuperación de información (RAG) y puede integrarse con un modelo de lenguaje; en la entrega base el planificador es determinista y no depende de servicios externos.

## Cómo se validó

- Todo el código generado con apoyo de IA fue **revisado y probado por el equipo**. El modelo se evalúa contra una línea base de persistencia con una partición temporal; el agente se evalúa con un banco de 15 preguntas (`eval/`) que verifica herramientas, citas y manejo de errores.
- El contenido del corpus del RAG se contrastó con las fuentes oficiales citadas (Resolución 2254 de 2017, protocolos del AMVA/SIATA y recomendaciones de salud pública).
- Las decisiones de diseño (control de calidad de los datos, elección del modelo, arquitectura del agente, vistas del dashboard) fueron tomadas y entendidas por el equipo, no delegadas ciegamente a la herramienta.

## Qué no hizo la IA

- No se usó la IA para inventar datos ni resultados: las métricas provienen de ejecutar el código sobre los datos reales del AMVA.
- El sistema entregado es una herramienta académica y no constituye consejo médico ni reemplaza los avisos oficiales del SIATA ni del AMVA.
