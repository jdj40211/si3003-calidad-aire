# Agente de calidad del aire del Valle de Aburrá — Informe

**SI3003 Inteligencia Artificial — Universidad EAFIT, 2026-2 · Idea 3.1**
**Equipo:** Juan David Sierra · Keita Ashizawa · Juan José Palacio (Integrante 3)

> Documento de máximo 4 páginas. El detalle de cada módulo está en el código (`src/`, `app/`, `eval/`) y en el `README.md`.

---

## 1. Problema y objetivo

En el Valle de Aburrá los episodios de contaminación por material particulado PM2.5 son frecuentes, sobre todo en las temporadas de marzo–abril y octubre–noviembre, cuando la baja dispersión atmosférica acumula partículas en el fondo del valle. El problema no es solo de medición: la ciudadanía recibe un número (el PM2.5 del día) que no sabe interpretar ni traducir en decisiones concretas ("¿puedo salir a correr?", "¿debo usar mascarilla?").

Construimos un asistente que (1) muestra las mediciones reales de las estaciones del Área Metropolitana del Valle de Aburrá (AMVA), (2) predice la categoría de calidad del aire del día siguiente con un modelo clásico, y (3) responde preguntas en lenguaje natural citando la normativa y los protocolos oficiales mediante un agente con RAG. Todo se integra en un dashboard interactivo.

## 2. Datos

**Fuente.** Conjunto "Calidad del Aire en Colombia" de datos.gov.co (identificador `g4t8-zkc3`, publicado por el SISAIRE/IDEAM). Se filtra la autoridad ambiental `AMVA` y las variables `PM2.5`, `PLiquida` (lluvia), `VViento` (velocidad del viento) y `TAire2` (temperatura), tomando solo las mediciones horarias (`duración = 60 min`) entre 2020 y 2025.

**Control de calidad.** La fuente presenta tramos con escalas inconsistentes (valores multiplicados por factores no constantes entre 2020 y 2023). En lugar de corregir valores arbitrariamente, el pipeline (`src/datos/procesar.py`) **descarta los meses por estación cuya distribución no es físicamente plausible** (reglas sobre la mediana y el percentil 99 de cada variable) y exige al menos 18 horas con dato para promediar un día. El reporte de cuánto se conserva queda en `data/processed/calidad_datos.csv` (por ejemplo, se conserva el 61 % de los meses-estación de PM2.5). Los datos procesados quedan versionados en `data/processed/` para que la app no dependa de la disponibilidad de la API.

**Resultado.** ~27.500 estación-días de PM2.5 diario en 29 estaciones, con su categoría ICA, más una serie meteorológica diaria del valle.

## 3. Parte 1 — Modelo clásico (IA tradicional)

**Tarea.** Clasificar la categoría ICA **del día siguiente** en tres clases: `0 = Buena`, `1 = Aceptable`, `2 = Dañina para grupos sensibles o peor`, usando como objetivo la categoría más crítica del día (`ica_max`).

**Características** (`src/modelo/caracteristicas.py`). Agregados diarios del valle (PM2.5 medio y máximo), meteorología (lluvia, viento, temperatura), rezagos de 1 a 3 días del PM2.5, medias/máximos móviles de 3 días y variables de calendario (mes, día de la semana, fin de semana, temporada crítica).

**Modelo y línea base.** Random Forest con `class_weight="balanced"` (para no ignorar las clases de alerta, que son minoritarias), con una **división temporal sin barajar** que respeta el orden de las fechas. Se compara contra una **línea base de persistencia** (mañana = hoy), que es un referente fuerte porque la calidad del aire tiene mucha inercia día a día. El módulo `src/modelo/predecir.py` entrena, evalúa, guarda el modelo y expone `predecir_manana()`, que es lo que consumen el dashboard y el agente. Las métricas (accuracy del modelo vs. línea base y F1 macro) se guardan en `eval/metricas_modelo.json`.

## 4. Parte 2 — Agente con RAG (IA moderna)

**Arquitectura** (`src/agente/`). Un loop de razonamiento-acción acotado por `T_max` iteraciones que, en cada turno, decide qué herramientas usar, las ejecuta, reúne la evidencia y redacta una respuesta con citas. Se registra una **traza** de cada pregunta (herramientas invocadas, argumentos, resultados) útil para depurar y evaluar.

**Herramientas** (`src/agente/herramientas.py`), cada una con nombre, descripción y esquema de argumentos:
- `get_pm25(estacion, dias)` — mediciones diarias recientes de una estación o del promedio del valle.
- `predict_tomorrow()` — categoría prevista del día siguiente (reutiliza el modelo de la Parte 1).
- `search_docs(consulta, k)` — recuperación sobre el corpus con la fuente de cada fragmento.

**RAG** (`src/agente/rag.py`). El corpus (`docs/corpus/`) contiene la Resolución 2254 de 2017 (categorías ICA y límites de PM2.5), el protocolo de episodios críticos del AMVA/SIATA y las recomendaciones de salud. Los documentos se fragmentan por párrafos y se indexan con TF-IDF; la consulta recupera los fragmentos más similares por coseno. Se eligió una recuperación ligera y **sin dependencias de red** para que la app y la evaluación corran de forma reproducible desde cero; la interfaz (`buscar(consulta, k)`) permite sustituirla por embeddings + FAISS sin tocar el resto del agente.

**Robustez.** Cada herramienta captura sus propios errores y devuelve `{"error": ...}` en lugar de lanzar excepciones, de modo que el agente informa el fallo en vez de romperse (p. ej. estación inexistente o datos no disponibles). Toda respuesta incluye la advertencia de que es una herramienta académica y no reemplaza los avisos del SIATA/AMVA.

## 5. Dashboard (Integrante 3)

El dashboard en Streamlit (`app/dashboard.py`) integra todo en cuatro vistas:
1. **Mapa** de las 29 estaciones, coloreadas por su última categoría ICA (colores de la Resolución 2254), con tabla de apoyo.
2. **Serie de tiempo** de PM2.5 con **selección de parámetros** (estación o promedio del valle, y rango de fechas) y líneas de referencia de las categorías.
3. **Predicción** del día siguiente con la categoría prevista, las probabilidades por clase y la comparación del modelo contra la línea base.
4. **Chat** con el agente, que muestra la respuesta, las herramientas usadas y las fuentes citadas.

Las vistas de predicción y chat consumen los módulos del equipo a través de interfaces limpias y **degradan con elegancia**: si un módulo aún no está disponible, la vista muestra un aviso en lugar de interrumpir la aplicación. Esto permitió desarrollar las tres partes en paralelo durante los tres días del cronograma.

## 6. Evaluación del agente (Integrante 3)

Se definió un banco de **15 preguntas** (`eval/preguntas.json`) que cubre datos, predicción, normativa, protocolos y salud. El script `eval/evaluar_agente.py` ejecuta el agente en cada una y verifica cuatro criterios: que use las herramientas esperadas, que la respuesta contenga palabras clave relevantes, que **cite una fuente** cuando corresponde y que no devuelva error. Genera un reporte legible en `eval/resultados.md` y un resumen en JSON, con la tasa de acierto global. Este diseño evalúa explícitamente las capacidades que pide la rúbrica: uso de ≥ 2 herramientas, RAG con citas y manejo de errores.

## 7. Reproducibilidad y cómo ejecutarlo



Todo corre sin claves de API ni conexión externa: los datos están versionados y el RAG es local.

## 8. Limitaciones y trabajo futuro

- La línea base de persistencia es exigente: en días estables la ganancia del modelo es moderada; el valor del modelo está sobre todo en anticipar los cambios de categoría.
- El RAG actual (TF-IDF) es simple y literal; migrar a embeddings + FAISS mejoraría las consultas parafraseadas.
- El corpus es acotado (tres documentos de referencia); ampliarlo con más normativa y boletines del SIATA daría respuestas más ricas.
- El sistema es una herramienta académica y **no** constituye consejo médico ni sustituye los avisos oficiales del SIATA ni del AMVA.
