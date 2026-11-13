# Agente de calidad del aire del Valle de Aburrá — Informe

**SI3003 Inteligencia Artificial — Universidad EAFIT, 2026-2 · Idea 3.1**
**Equipo:** Juan David Sierra · Keita Ashizawa · Juan José Palacio (Integrante 3)

> Documento de máximo 4 páginas. El detalle de cada módulo está en el código (`src/`, `app/`, `notebook/`,`eval/`) y en el `README.md`.

---

## 1. Problema y objetivo

En el Valle de Aburrá los episodios de contaminación por material particulado PM2.5 son frecuentes, sobre todo en las temporadas de marzo–abril y octubre–noviembre, cuando la baja dispersión atmosférica acumula partículas en el fondo del valle. El problema no es solo de medición: la ciudadanía recibe un número (el PM2.5 del día) que no sabe interpretar ni traducir en decisiones concretas ("¿puedo salir a correr?", "¿debo usar mascarilla?").

Construimos un asistente que (1) muestra las mediciones reales de las estaciones del Área Metropolitana del Valle de Aburrá (AMVA), (2) predice la categoría de calidad del aire del día siguiente con un modelo clásico, y (3) responde preguntas en lenguaje natural citando la normativa y los protocolos oficiales mediante un agente con RAG. Todo se integra en un dashboard interactivo.

## 2. Datos

**Fuente.** Conjunto *"Calidad del Aire en Colombia"* de `datos.gov.co` (identificador `g4t8-zkc3`, publicado por el SISAIRE/IDEAM). Se filtra la autoridad ambiental AMVA y las variables `PM2.5`, `PLiquida` (lluvia), `VViento` (velocidad del viento) y `TAire2` (temperatura), tomando mediciones horarias entre 2020 y 2025.

**Control de calidad e imputación sin fuga de datos.** Dado que la fuente presenta tramos con escalas inconsistentes y vacíos históricos (cerca del 55 % de los días carecen de reporte meteorológico completo), el flujo descarta meses-estación con distribuciones físicamente no plausibles y exige al menos 18 horas válidas por día, consolidando el porcentaje de meses válidos en `calidad_datos.csv` (`TAire2`: 100 %, `PM25`: 61.1 %, `PLiquida`: 36.9 %, `VViento`: 33.7 %). Posteriormente, se reindexa la serie sobre un **calendario diario continuo** (2.192 días) para evitar desplazamientos erróneos en los rezagos, se crea una bandera explícita de ausencia (`is_meteo_missing`), se imputa la lluvia faltante con `0` y se aplica propagación causal limitada (`ffill(limit=3)`) en viento y temperatura; los vacíos prolongados se rellenan **únicamente con la mediana del conjunto de entrenamiento** tras la partición temporal.

**Resultado.** Se integran cuatro tablas procesadas y versionadas (`pm25_diario.csv` con 27.553 estación-días en **28 estaciones**, `meteo_diario.csv` con 971 días reportados, el catálogo espacial `estaciones.csv` y `calidad_datos.csv`).

## 3. Parte 1 — Modelo clásico (IA tradicional)

**Tarea.** Clasificar la categoría máxima del ICA **del día siguiente ($t+1$)** en tres clases (`0 = Buena`, `1 = Aceptable`, `2 = Dañina a grupos sensibles o peor`), empleando como objetivo `ica_max`.

**Ingeniería de características (24 variables).** A partir de la integración multifuente se construyen: (a) **agregados diarios y espaciales**, incluyendo promedios y máximos de $\text{PM}_{2.5}$, promedio ponderado por horas válidas (`pm25_weighted_horas`), **latitud ponderada por $\text{PM}_{2.5}$** (`pm25_weighted_lat`, para capturar desplazamientos norte-sur de la contaminación), cobertura de red (`pct_cobertura_red`) y municipios activos; (b) **meteorología y confiabilidad**, integrando lluvia, viento, temperatura, `is_meteo_missing` y un índice diario de confiabilidad (`data_reliability_score`) ponderado según `calidad_datos.csv`; y (c) **dinámica temporal**, con rezagos de 1 a 3 días, variación diaria (`pm25_diff_1d`), volatilidad y máximo móvil de 3 días (`shift(1)` para evitar *data leakage*), codificación cíclica del mes (`month_sin`, `month_cos`), fin de semana y temporada crítica (marzo–abril y octubre–noviembre).

**Modelo propio en NumPy y comparación con línea base.** Se implementó desde cero en **NumPy** una **Regresión Logística Multiclase (Softmax)** con estandarización Z-score interna, regularización $L_2$ ($\lambda = 0.01$), descenso de gradiente y ponderación balanceada de clases normalizada a media unitaria (`class_weight='balanced'`). Los datos se dividen cronológicamente (`shuffle=False`, 80 % entrenamiento / 20 % prueba, 431 días de evaluación) y se comparan frente a una **línea base de persistencia** ($\hat{y}_{t+1} = y_t$) y un **Random Forest balanceado** de referencia:

| Modelo | Exactitud (*Accuracy*) | F1-Score Macro | *Recall* Clase Dañina (`2.0`) |
| :--- | :---: | :---: | :---: |
| Línea Base (Persistencia) | 94,94 % | 0,3240 | 0,0000 |
| Random Forest Balanceado (Referencia) | 96,32 % | 0,3680 | 0,2222 |
| **Regresión Logística Propia (NumPy)** | **93,04 %** | **0,3801** | **0,3333** |

Mientras que la persistencia es incapaz de anticipar episodios críticos (`Recall = 0.0000`), el modelo propio en NumPy logra detectar **el 33,3 % de los días dañinos** y obtiene el mayor **F1-Score Macro (0,3801)**. El flujo de predicción se expone mediante `predecir_manana()` para su consumo en el dashboard y el agente.

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

* **Desbalance severo de clases y compromiso *Precision–Recall*:** En el periodo reciente de prueba (431 días), la clase `1 = Aceptable` concentra el **97,47 %** de los registros (420 días), frente a solo 9 días dañinos (`2.0`) y 2 días buenos (`0.0`). Aunque la ponderación balanceada en el modelo propio permite anticipar episodios críticos (`Recall = 0,3333` frente a `0,0000` de la persistencia), incrementa las falsas alarmas y reduce ligeramente la exactitud global.
* **Cobertura meteorológica parcial y linealidad:** La ausencia histórica de ~55 % en variables como viento y lluvia introduce incertidumbre en transiciones climáticas bruscas; además, al ser un clasificador lineal, la regresión logística tiene menor capacidad para modelar inversiones térmicas altamente no lineales. A futuro se propone incorporar pronósticos meteorológicos exógenos y datos de tráfico.
* **Alcance del corpus RAG y dependencia de LLM:** El corpus resume el POECA de 2016 (sin incluir su actualización de 2018, Acuerdo 04) ni guías oficiales sobre tipos de mascarilla. Asimismo, sin clave de API externa el sistema opera con el agente de respaldo por reglas, de menor flexibilidad semántica.
* **Aviso académico:** Este sistema es una herramienta experimental con fines académicos y **no** constituye consejo médico ni sustituye los avisos oficiales del SIATA ni del AMVA.
