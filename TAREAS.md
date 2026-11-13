# Reparto de tareas

Equipo de 3. Entrega: **viernes 13 de noviembre de 2026, 6:00 p. m.** Cada integrante envía el correo a jipadillab@eafit.edu.co con el asunto `si3003-AI-grupo-nombre`.

Regla del equipo: **cada quien sube sus propios commits de su parte**, en ramas cortas y con PR a `main`. La nota es grupal pero se evalúa el aporte individual.

| Integrante | Responsable de | Criterios de la rúbrica |
|---|---|---|
| Juan David Sierra | Agente LLM: loop con `T_max`, tool calling, RAG (corpus, embeddings, FAISS) e integración final | Agente 20 %, Reproducibilidad 10 % |
| Keita Ashizawa | Datos y Parte 1: descarga, limpieza, EDA, modelo propio con métrica frente a la línea base | Parte 1 20 %, Rigor 15 % (parte del modelo) |
| Juan José Palacio | Dashboard en Streamlit (mapa, serie, predicción, chat), evaluación del agente (10 a 15 preguntas), informe de 4 páginas | Dashboard 10 %, Interacción 15 %, Rigor 15 % (parte del agente) |
| Todos | README final, declaración de uso de IA, revisión cruzada y envío del correo | Presentación 5 %, Declaración 5 % |

## Cronograma real (quedan 3 días)

| Día | Meta |
|---|---|
| Martes 10 | Repo, datos descargados y procesados, EDA inicial |
| Miércoles 11 | Modelo de la Parte 1 con métrica; agente mínimo con una herramienta; esqueleto del dashboard |
| Jueves 12 | RAG y las tres herramientas; dashboard completo; evaluación del agente; congelar código |
| Viernes 13 (antes de las 6 p. m.) | Informe, declaración de IA, prueba desde cero siguiendo el README y envío de los tres correos |

## Lista de verificación de entrega

- [x] La app corre desde cero siguiendo solo el README (verificado el 11 nov clonando el repo en una carpeta nueva)
- [x] Métrica del modelo frente a la línea base (`eval/metricas_modelo.json`)
- [x] **Modelo de la Parte 1 implementado por el equipo**: hoy es un Random Forest de scikit-learn, y el enunciado exige una implementación propia (por ejemplo, Naive Bayes o regresión logística escritos con numpy)
- [x] Agente LLM con RAG híbrido, 3 herramientas, citas y manejo de errores
- [x] Al menos 2 visualizaciones y selección de parámetros (mapa, serie de tiempo, predicción)
- [x] 15 preguntas de evaluación del agente, LLM contra reglas (`eval/resultados.md`)
- [x] Informe (máximo 4 páginas) — falta actualizar la sección 3 cuando cambie el modelo
- [x] Declaración de uso de IA generativa — cada integrante debe completar qué herramienta usó en su parte
- [ ] Los tres correos enviados
