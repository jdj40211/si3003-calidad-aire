# Agente de calidad del aire del Valle de Aburrá

Proyecto final de **SI3003 Inteligencia Artificial** (Universidad EAFIT, 2026-2), idea 3.1 del enunciado.

**Problema.** Los ciudadanos no entienden qué significa el PM2.5 del día ni qué hacer al respecto.
Construimos un asistente que consulta las mediciones reales de las estaciones del Área Metropolitana del Valle de Aburrá (AMVA), predice la categoría de calidad del aire del día siguiente y responde preguntas citando la normativa y los protocolos de episodios críticos.

## Componentes

| Parte | Qué es | Estado |
|---|---|---|
| Datos reales | PM2.5 y meteorología horaria 2020–2025 de las estaciones del AMVA (datos.gov.co, IDEAM/SISAIRE) | Acceso verificado |
| Parte 1 (IA clásica) | Clasificador implementado por el equipo para la categoría del día siguiente, comparado contra una línea base de persistencia | Por hacer |
| Parte 2 (IA moderna) | Agente LLM con RAG sobre normativa y protocolos, con las herramientas `get_pm25`, `predict_tomorrow` y `search_docs` | Por hacer |
| Dashboard | Streamlit: mapa de estaciones, serie de tiempo, predicción y chat con el agente | Por hacer |

## Fuente de datos

- **Calidad del Aire en Colombia**, datos.gov.co, identificador [`g4t8-zkc3`](https://www.datos.gov.co/resource/g4t8-zkc3) (SISAIRE, IDEAM). Se filtra la autoridad ambiental `AMVA` y las variables `PM2.5`, `PLiquida` (lluvia), `VViento` (velocidad del viento) y `TAire2` (temperatura).
- Plan B: los históricos ya descargados quedan en `data/processed/` para que la app no dependa de la API.

## Estructura

```
src/datos/     descarga y limpieza de datos
src/modelo/    modelo de la Parte 1 (implementación propia) y su evaluación
src/agente/    loop del agente, herramientas y RAG
app/           dashboard en Streamlit
docs/corpus/   documentos para el RAG (normativa, protocolos, recomendaciones)
notebooks/     EDA y experimentos
eval/          preguntas de prueba del agente y resultados
```

El reparto de tareas y el cronograma están en [`TAREAS.md`](TAREAS.md).

> Este sistema es una herramienta académica. No es consejo médico ni reemplaza los avisos oficiales del SIATA o del AMVA.
