# Agente de calidad del aire del Valle de Aburrá

Proyecto final de **SI3003 Inteligencia Artificial** (Universidad EAFIT, 2026-2), idea 3.1 del enunciado.

**Equipo:** Juan David Sierra · Keita Ashizawa · Juan José Palacio

**Problema.** Los ciudadanos no entienden qué significa el PM2.5 del día ni qué hacer al respecto.
Construimos un asistente que consulta las mediciones reales de las estaciones del Área Metropolitana del Valle de Aburrá (AMVA), predice la categoría de calidad del aire del día siguiente y responde preguntas citando la norma colombiana y el protocolo de episodios críticos.

> Herramienta académica. No es consejo médico ni reemplaza los avisos oficiales del SIATA o del Área Metropolitana.

## Componentes

| Parte | Qué es | Dónde |
|---|---|---|
| Datos reales | PM2.5, lluvia, viento y temperatura horarios 2020–2025 de las estaciones del AMVA (datos.gov.co, SISAIRE-IDEAM), con control de calidad y agregación diaria | `src/datos/`, `data/processed/` |
| Parte 1 (IA clásica) | Clasificador de la categoría de calidad del aire del día siguiente, comparado contra la línea base de persistencia (mañana = hoy) | `src/modelo/`, `notebooks/` |
| Parte 2 (IA moderna) | Agente LLM con tool calling (`get_pm25`, `predict_tomorrow`, `search_docs`), loop acotado por `T_MAX` y RAG híbrido sobre documentos oficiales | `src/agente/`, `docs/corpus/` |
| Dashboard | Streamlit: mapa de estaciones, serie de tiempo, predicción y chat con el agente | `app/dashboard.py` |
| Evaluación | Métricas del modelo frente a la línea base y 15 preguntas de prueba del agente | `eval/` |

## Cómo correrlo

Requiere Python 3.10 o superior. Los datos procesados ya vienen en el repositorio, así que no hace falta descargar nada para usar la app.

```bash
git clone https://github.com/jdj40211/si3003-calidad-aire.git
cd si3003-calidad-aire
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

Edite `.env` y ponga una clave de API para el LLM (ver la sección siguiente). Después:

```bash
streamlit run app/dashboard.py
```

La app abre en http://localhost:8501. La primera vez tarda un poco más porque descarga el modelo de embeddings (unos 220 MB) y entrena el clasificador; las siguientes veces usa lo que quedó guardado.

### Clave del LLM

El agente usa un endpoint compatible con la API de OpenAI. Se puede usar cualquiera de estos, con capa gratuita:

| Proveedor | Variable en `.env` | Modelo por defecto | Cómo obtener la clave |
|---|---|---|---|
| NVIDIA NIM | `NVIDIA_API_KEY` | `nvidia/nemotron-3.5-super-vl-120b-a12b` | https://build.nvidia.com |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | https://console.groq.com |

Para cambiar de modelo se usa `LLM_MODELO`, y para forzar un proveedor, `LLM_PROVEEDOR` (`nvidia` o `groq`).

**Sin clave la app también funciona:** el chat usa un agente de respaldo que elige las herramientas con reglas y arma la respuesta con plantillas, y el dashboard lo avisa. Ese respaldo también entra si el proveedor del LLM falla durante la demo.

## Comandos útiles

| Qué | Comando |
|---|---|
| Preguntarle al agente desde la terminal | `python -m src.agente.agente "¿Qué medidas se toman en alerta roja?"` |
| Probar la búsqueda del RAG | `python -m src.agente.rag "límite diario de PM2.5"` |
| Reentrenar y evaluar el modelo | `python -m src.modelo.predecir` |
| Evaluar el agente (15 preguntas, LLM contra reglas) | `python -m eval.evaluar_agente` |
| Volver a descargar los datos (unos 180 MB) | `python -m src.datos.descargar` |
| Volver a procesar los datos | `python -m src.datos.procesar` |

## Cómo funciona el agente

```
pregunta ──► LLM ──► ¿necesita datos? ──sí──► herramienta ──► resultado o error ──┐
              ▲                                                                     │
              └─────────────────── observación ◄──────────────────────────────────┘
                     (máximo T_MAX = 5 iteraciones; después debe responder)
```

- **`get_pm25(estacion, dias)`:** mediciones diarias de una estación o del promedio del valle.
- **`predict_tomorrow()`:** categoría prevista para el día siguiente con el modelo de la Parte 1.
- **`search_docs(consulta, k)`:** RAG. Los documentos se parten por secciones y se buscan con embeddings multilingües (`paraphrase-multilingual-MiniLM-L12-v2` con fastembed, sin GPU) en un índice FAISS, combinados con TF-IDF mediante Reciprocal Rank Fusion. TF-IDF rescata siglas y términos exactos (por ejemplo "ND" o "naranja") que el modelo de embeddings solo no encontraba.

Los errores de las herramientas vuelven al LLM como observación, no como excepción. Cada dato que sale de un documento se cita con el documento y la sección. Las mediciones se citan como datos del SISAIRE-IDEAM y la predicción como resultado del modelo del proyecto.

## Resultados

**Agente** (`eval/resultados.md`): en la última corrida, el agente LLM aprobó 15 de 15 preguntas y el de reglas 12 de 15. El LLM eligió la herramienta correcta en 15 de 15 y citó la fuente en todas las que lo requerían. Entre corridas el LLM obtuvo de 13 a 15, porque no responde exactamente igual cada vez. El agente de reglas falla, por ejemplo, en "¿cuál es el valor máximo anual permitido?": detecta "PM2.5" y consulta las mediciones en lugar de la norma. La pregunta 13 (qué mascarilla usar) no tiene respuesta en los documentos y el agente LLM lo dice en lugar de inventarla.

**Modelo** (`eval/metricas_modelo.json`): resultados del clasificador frente a la línea base de persistencia, con una partición temporal.

## Fuentes

Datos:
- **Calidad del Aire en Colombia**, datos.gov.co, [`g4t8-zkc3`](https://www.datos.gov.co/resource/g4t8-zkc3) (SISAIRE, IDEAM), filtrado a la autoridad ambiental AMVA.

Documentos del RAG (`docs/corpus/`; el texto original extraído está en `docs/fuentes/`):
- Ministerio de Ambiente y Desarrollo Sostenible, [Resolución 2254 de 2017](https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=82634): norma de calidad del aire e ICA.
- Área Metropolitana del Valle de Aburrá, [Acuerdo Metropolitano 15 de 2016](https://www.siclas.org/wp-content/uploads/2017/02/AcuerdoProtocoloPOECA_FINAL.pdf): protocolo del POECA.
- SIATA, [reporte diario del ICA de PM2.5](https://siata.gov.co/CalidadAire/ReporteDiario/ICADiario_POECA.pdf).
- OMS, [nota descriptiva sobre la contaminación del aire ambiente y la salud](https://www.who.int/es/news-room/fact-sheets/detail/ambient-(outdoor)-air-quality-and-health).

## Limitaciones

- **Calidad de la fuente:** entre 2020 y 2023 muchas estaciones publican PM2.5, viento y lluvia multiplicados por 10 o 100 sin un factor constante. Esos meses se descartan, no se corrigen; el reporte está en `data/processed/calidad_datos.csv`. El viento y la temperatura válidos solo existen para 2024 y 2025.
- **Sin tiempo real:** los datos llegan hasta el 31 de diciembre de 2025, y el agente siempre dice la fecha de la medición.
- **Clases desbalanceadas:** menos del 2 % de los días-estación son dañinos, así que el modelo tiene poca experiencia con episodios críticos.
- **Protocolo:** el corpus resume el POECA de 2016; existe una actualización de 2018 (Acuerdo Metropolitano 04) que no se incorporó.
- **El LLM puede equivocarse:** la evaluación usa palabras clave y una revisión manual de fidelidad, y no garantiza que cada respuesta sea correcta.

## Estructura

```
src/datos/      descarga y limpieza de datos
src/modelo/     modelo de la Parte 1 y su evaluación
src/agente/     loop del agente, herramientas y RAG
app/            dashboard en Streamlit
docs/corpus/    documentos del RAG, con su fuente
docs/fuentes/   texto extraído de los documentos oficiales
docs/           informe y declaración de uso de IA
notebooks/      EDA y experimentos
eval/           preguntas de prueba, resultados y métricas
```

El reparto de tareas está en [`TAREAS.md`](TAREAS.md) y la declaración de uso de IA generativa, en [`docs/declaracion_uso_ia.md`](docs/declaracion_uso_ia.md).
