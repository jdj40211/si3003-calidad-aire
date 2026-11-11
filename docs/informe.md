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

**Arquitectura** (`src/agente/agente.py`). Un LLM con *tool calling* (por defecto `nemotron-3.5-super-vl` en NVIDIA NIM, por medio del SDK de OpenAI; Groq como alternativa) ejecuta un loop acotado por `T_MAX = 5` iteraciones: en cada turno decide si llama una herramienta o si ya puede responder; el resultado de la herramienta, incluido un posible error, vuelve al LLM como observación. Si se agotan las iteraciones, se le pide una respuesta final sin más herramientas, y se evita repetir una llamada con los mismos argumentos. El prompt exige citar cada dato con el documento y la sección, decir la fecha de las mediciones y no dar consejo médico. Se registra una **traza** de cada pregunta (modo, herramientas, argumentos, resultados y fuentes citadas). Si no hay clave de API o el proveedor falla, responde un **agente de respaldo por reglas** que elige las herramientas por palabras clave, para que el chat nunca quede sin respuesta durante la demo.

**Herramientas** (`src/agente/herramientas.py`), cada una con nombre, descripción y esquema de argumentos:
- `get_pm25(estacion, dias)` — mediciones diarias recientes de una estación o del promedio del valle.
- `predict_tomorrow()` — categoría prevista del día siguiente (reutiliza el modelo de la Parte 1).
- `search_docs(consulta, k)` — recuperación sobre el corpus con la fuente de cada fragmento.

**RAG** (`src/agente/rag.py`). El corpus (`docs/corpus/`) se construyó a partir de documentos oficiales, cuyo texto extraído queda en `docs/fuentes/`: la Resolución 2254 de 2017 (límite diario de 37 µg/m³, niveles de prevención, alerta y emergencia, y tabla del ICA con sus efectos), el protocolo del POECA del Área Metropolitana (Acuerdo 15 de 2016: niveles, medidas y temporadas críticas), el reporte diario del ICA del SIATA y la nota descriptiva de la OMS sobre contaminación y salud. Los documentos se fragmentan por secciones, y cada fragmento conserva el documento, la sección y la URL para citarlo. La búsqueda es **híbrida**: embeddings multilingües (`paraphrase-multilingual-MiniLM-L12-v2`, ejecutado con fastembed/ONNX, sin GPU) en un índice **FAISS** de producto interno, combinados con TF-IDF mediante **Reciprocal Rank Fusion** (k = 60). Los embeddings capturan el significado de preguntas parafraseadas; TF-IDF rescata siglas y términos exactos ("ND", "naranja") que el modelo pequeño de embeddings, por sí solo, no recuperaba.

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

**Resultados.** El script corre las 15 preguntas con el agente LLM y con el de reglas. En la última corrida el LLM aprobó 15 de 15 (herramienta correcta en 15 de 15 y cita en todas las que lo requerían) y el de reglas 12 de 15; entre corridas el LLM obtuvo de 13 a 15, porque su salida varía. El agente de reglas falla, por ejemplo, en «¿cuál es el valor máximo anual permitido?»: detecta «PM2.5» y consulta las mediciones en lugar de la norma. La pregunta 13 (qué mascarilla usar) no tiene respuesta en los documentos, y el LLM lo dice en lugar de inventarla. Una revisión manual encontró que una versión anterior del prompt citaba documentos para afirmaciones que no estaban en el fragmento; se corrigió exigiendo que la cita solo acompañe lo que el fragmento dice. Las palabras clave de tres preguntas se corrigieron porque contradecían la norma (por ejemplo, esperaban «37» para la categoría que según la Resolución 2254 empieza en 38 µg/m³); el motivo de cada cambio queda en `preguntas.json`.

## 7. Reproducibilidad y cómo ejecutarlo

El README tiene los pasos completos: crear un entorno virtual, `pip install -r requirements.txt`, copiar `.env.example` a `.env` con una clave de NVIDIA NIM o Groq, y `streamlit run app/dashboard.py`. Los datos procesados están versionados, así que la app no depende de la API de datos.gov.co. La primera ejecución descarga el modelo de embeddings (unos 220 MB) y entrena el clasificador; las siguientes reutilizan lo guardado. Se verificó clonando el repositorio en una carpeta nueva y siguiendo solo el README: el dashboard y el chat funcionaron en unos 45 s la primera vez. Sin clave de API, la app también corre con el agente de respaldo.

## 8. Limitaciones y trabajo futuro

- La línea base de persistencia es exigente: en días estables la ganancia del modelo es moderada; el valor del modelo está sobre todo en anticipar los cambios de categoría.
- El corpus resume el POECA de 2016; existe una actualización de 2018 (Acuerdo Metropolitano 04) que no se incorporó. Tampoco incluye recomendaciones oficiales sobre mascarillas.
- El agente depende de un proveedor externo de LLM: sin clave o sin conexión, responde el agente de respaldo, con menos precisión. La evaluación por palabras clave no garantiza que cada respuesta sea correcta, y el LLM puede variar entre corridas.
- El sistema es una herramienta académica y **no** constituye consejo médico ni sustituye los avisos oficiales del SIATA ni del AMVA.
