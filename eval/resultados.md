# Resultados de la evaluación del agente

Integrante 3: Juan José Palacio. Comparación con el agente LLM: Juan David Sierra.

**Agente evaluado:** LLM (nvidia/nemotron-3.5-super-vl-120b-a12b)

**Preguntas:** 15 · **Aprobadas:** 15 · **Tasa de acierto:** 100.0%

Cada caso se considera aprobado si el agente usó las herramientas esperadas, incluyó al menos una palabra clave relevante, citó una fuente cuando correspondía y no devolvió error.

| # | Categoría | Herramientas | Cita | Claves | Resultado |
|---|---|---|---|---|---|
| 1 | normativa | ✓ | ✓ | ✓ | APRUEBA |
| 2 | prediccion | ✓ | ✓ | ✓ | APRUEBA |
| 3 | datos | ✓ | ✓ | ✓ | APRUEBA |
| 4 | protocolo | ✓ | ✓ | ✓ | APRUEBA |
| 5 | salud | ✓ | ✓ | ✓ | APRUEBA |
| 6 | protocolo | ✓ | ✓ | ✓ | APRUEBA |
| 7 | datos | ✓ | ✓ | ✓ | APRUEBA |
| 8 | normativa | ✓ | ✓ | ✓ | APRUEBA |
| 9 | normativa | ✓ | ✓ | ✓ | APRUEBA |
| 10 | salud | ✓ | ✓ | ✓ | APRUEBA |
| 11 | prediccion | ✓ | ✓ | ✓ | APRUEBA |
| 12 | protocolo | ✓ | ✓ | ✓ | APRUEBA |
| 13 | fuera_de_corpus | ✓ | ✓ | ✓ | APRUEBA |
| 14 | datos | ✓ | ✓ | ✓ | APRUEBA |
| 15 | normativa | ✓ | ✓ | ✓ | APRUEBA |

## Comparación de agentes

| Agente | Aprobadas | Herramienta correcta | Cita cuando se espera | Palabras clave |
|---|---|---|---|---|
| LLM (nvidia/nemotron-3.5-super-vl-120b-a12b) | 15/15 | 15/15 | 15/15 | 15/15 |
| Reglas (respaldo) | 12/15 | 14/15 | 14/15 | 13/15 |

## Notas de rigor

- El LLM no responde exactamente igual en cada corrida (temperatura 0,1): entre corridas el agente LLM obtuvo 13, 14 y 15 de 15. La tabla de arriba es la de la última corrida.
- Las palabras clave de las preguntas 1, 5 y 10 se corrigieron porque se escribieron para un corpus anterior sin fuentes: la 1 esperaba '37', pero según la Resolución 2254 de 2017 la categoría dañina para grupos sensibles empieza en 38 µg/m³; la 5 y la 10 esperaban 'interior', que el POECA no menciona. El motivo de cada cambio está en el campo 'nota' de preguntas.json.
- La pregunta 13 (tipo de mascarilla) no tiene respuesta en el corpus: se espera que el agente lo diga en lugar de inventar.
- Revisión manual de fidelidad: en una versión anterior del prompt el LLM citaba documentos para afirmaciones que no estaban en el fragmento (por ejemplo, 'al hacer ejercicio se respira más profundo' citado a la Resolución 2254). Se corrigió exigiendo que la cita solo acompañe lo que el fragmento dice y que el conocimiento general vaya sin cita, introducido con 'En general'.

## Detalle de cada pregunta

### 1. ¿Qué significa la categoría dañina para grupos sensibles?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** res2254_norma_calidad_aire.md
- **Respuesta:** Significa que el aire tiene niveles de PM2.5 que pueden afectar la salud de las personas más vulnerables, como niños, adultos mayores y quienes tienen enfermedades cardíacas o pulmonares (Resolución 2254 de 2017, Puntos de corte del ICA para PM2.5). En esta categoría, los grupos sensibles pueden presentar efectos sobre la salud, mientras que el resto de la población probablemente no se vea afectada (Resolución 2254 de 2017, Índice de Calidad del Aire, ICA). En general, se recomienda reducir actividades al aire libre prolongadas o intensas si perteneces a un grupo sensible. Consulta los avisos oficiales del SIATA y del Área Metropolitana del Valle de Aburrá para conocer las medidas específicas.

### 2. ¿Cómo estará la calidad del aire mañana en el valle?
- **Herramientas usadas:** predict_tomorrow (esperadas: predict_tomorrow)
- **Fuentes citadas:** —
- **Respuesta:** Mañana se espera calidad del aire Aceptable en el valle, con 93,3 % de probabilidad (Modelo del proyecto). Hoy el promedio del valle fue de 18,12 µg/m³ de PM2,5, con un máximo de 25,1 µg/m³ (Datos: SISAIRE-IDEAM, promedio del valle, 31 de diciembre de 2025). En general, una categoría Aceptable puede afectar a personas muy sensibles a la contaminación. Consulta los avisos oficiales del SIATA y del Área Metropolitana si perteneces a un grupo de riesgo.

### 3. ¿Cuál es el PM2.5 más reciente de la estación Altavista?
- **Herramientas usadas:** get_pm25 (esperadas: get_pm25)
- **Fuentes citadas:** —
- **Respuesta:** El PM2.5 más reciente de la estación Altavista es de 25,1 µg/m³, con categoría ICA "Aceptable", medido el 31 de diciembre de 2025 (Datos: SISAIRE-IDEAM, estación ALTAVISTA, 2025-12-31).

### 4. ¿Qué dice el protocolo cuando hay alerta naranja?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** poeca_acuerdo15_2016.md
- **Respuesta:** Cuando hay alerta naranja, el protocolo POECA ordena informar el episodio y publicar diariamente la evolución del ICA, recomendar a la comunidad reducir la exposición de los grupos sensibles y minimizar emisiones, sugerir a los establecimientos educativos reducir el esfuerzo prolongado al aire libre, y hacer más campañas de educación en sitios de atención en salud (Fuente: POECA: protocolo para episodios críticos de contaminación en el Valle de Aburrá, Medidas en Alerta naranja). La alerta naranja corresponde a un ICA de 101 a 150, es decir 35,5 a 55,4 µg/m³ de PM2.5 en promedio de 24 horas (Fuente: POECA: protocolo para episodios críticos de contaminación en el Valle de Aburrá, Niveles de contingencia por PM2.5 (Artículo 11)). En general, este nivel indica calidad del aire aceptable pero con riesgo para grupos sensibles. Consulta los avisos oficiales del SIATA y del Área Metropolitana del Valle de Aburrá.

### 5. ¿Puedo hacer ejercicio al aire libre si el aire está dañino para la salud?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** res2254_norma_calidad_aire.md, poeca_acuerdo15_2016.md
- **Respuesta:** No se recomienda hacer ejercicio al aire libre cuando el aire está dañino para la salud, porque al hacer ejercicio se respira más profundo y se inhala más contaminación (Fuente: Resolución 2254 de 2017, Índice de Calidad del Aire, ICA (Artículos 18 a 21, Tabla 5)). En niveles naranja, los grupos sensibles pueden presentar efectos sobre la salud; en rojo, todos pueden empezar a experimentarlos (Fuente: Resolución 2254 de 2017, Índice de Calidad del Aire, ICA (Artículos 18 a 21, Tabla 5)). El protocolo POECA recomienda reducir el esfuerzo prolongado al aire libre en alerta naranja y que niños y adolescentes no realicen actividades al aire libre en alerta roja fase II (Fuente: POECA: protocolo para episodios críticos de contaminación en el Valle de Aburrá, Medidas en Alerta naranja y Medidas en Alerta roja fase II). En general, es mejor hacer ejercicio en interiores o en horarios con mejor calidad del aire. Consulta los avisos oficiales del SIATA y del Área Metropolitana antes de salir.

### 6. ¿Cuáles son las temporadas críticas de contaminación en el Valle de Aburrá?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** poeca_acuerdo15_2016.md
- **Respuesta:** Las temporadas críticas son febrero a abril y octubre a noviembre, según el protocolo POECA del Área Metropolitana (Fuente: POECA: protocolo para episodios críticos de contaminación en el Valle de Aburrá, Temporadas críticas (Artículo 15)). En marzo, la transición entre la temporada seca y la primera temporada de lluvias genera las concentraciones más altas de PM10 y PM2.5 del año (Fuente: POECA: protocolo para episodios críticos de contaminación en el Valle de Aburrá, Temporadas críticas (Artículo 15)). En noviembre, al pasar de la temporada de lluvias a la seca, las concentraciones vuelven a subir (Fuente: POECA: protocolo para episodios críticos de contaminación en el Valle de Aburrá, Temporadas críticas (Artículo 15)). Esto ocurre porque el valle es una cuenca atmosférica rodeada de montañas que dificulta la dispersión de los contaminantes (Fuente: POECA: protocolo para episodios críticos de contaminación en el Valle de Aburrá, Por qué el valle acumula contaminantes (Artículo 3)). En general, los episodios críticos pueden presentarse en cualquier momento del año cuando se constaten eventos de alta contaminación. Consulte los avisos oficiales del SIATA y del Área Metropolitana para conocer el estado actual y las recomendaciones de salud.

### 7. ¿Qué nivel de PM2.5 tiene el valle en los últimos días?
- **Herramientas usadas:** get_pm25 (esperadas: get_pm25)
- **Fuentes citadas:** —
- **Respuesta:** En los últimos 7 días el promedio del valle estuvo entre 14.33 y 20.22 µg/m³ de PM2.5, con el valor más reciente de 18.12 µg/m³ el 31 de diciembre de 2025 (Datos: SISAIRE-IDEAM, promedio del valle, 2025-12-31). En general, estos valores se sitúan en rangos moderados, pero para saber si representan un riesgo para la salud se deben consultar los niveles oficiales del SIATA y del Área Metropolitana.

### 8. ¿Qué es el PM2.5 y por qué es peligroso para la salud?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** oms_contaminacion_aire_salud.md, res2254_norma_calidad_aire.md
- **Respuesta:** El PM2.5 son partículas finas en suspensión de menos de 2,5 micrómetros de diámetro, presentes en la contaminación del aire (Fuente: OMS: contaminación del aire ambiente y salud, Material particulado y efectos en la salud). Su exposición causa enfermedades cardiovasculares y respiratorias, cánceres, accidentes cerebrovasculares, cardiopatías y neumopatías crónicas y agudas, como el asma (Fuente: OMS: contaminación del aire ambiente y salud, Material particulado y efectos en la salud). Según la Resolución 2254 de 2017, cuando el ICA por material particulado supera 100, los grupos sensibles —personas con enfermedad cardíaca o pulmonar, adultos mayores y niños— corren mayor riesgo (Fuente: Resolución 2254 de 2017: norma de calidad del aire en Colombia, Índice de Calidad del Aire, ICA (Artículos 18 a 21, Tabla 5)). En general, al ser tan pequeñas, estas partículas pueden penetrar profundamente en los pulmones y llegar al torrente sanguíneo. Consulta los avisos oficiales del SIATA y del Área Metropolitana del Valle de Aburrá cuando haya riesgo para la salud.

### 9. ¿Qué norma colombiana regula la calidad del aire?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** res2254_norma_calidad_aire.md
- **Respuesta:** La norma colombiana que regula la calidad del aire es la Resolución 2254 de 2017, que establece los límites máximos permisibles de contaminantes y el Índice de Calidad del Aire (ICA) (Fuente: Resolución 2254 de 2017: norma de calidad del aire en Colombia, Meta a 2030 (Artículo 3, Tabla 2)). En general, esta resolución también define los niveles de prevención, alerta y emergencia para proteger la salud.

### 10. ¿Qué recomiendan para los niños cuando la calidad del aire es mala?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** poeca_acuerdo15_2016.md
- **Respuesta:** Cuando el aire es dañino para grupos sensibles (ICA naranja o peor), los niños deben evitar el esfuerzo prolongado al aire libre (Fuente: POECA del Área Metropolitana, Medidas en Alerta naranja y Alerta roja fase I). En Alerta roja fase II, los establecimientos educativos reciben la instrucción de que los niños y adolescentes no realicen actividades al aire libre (Fuente: POECA del Área Metropolitana, Medidas en Alerta roja fase II). La Resolución 2254 de 2017 señala que los niños son un grupo sensible y pueden presentar efectos sobre la salud con ICA de 101 en adelante (Fuente: Resolución 2254 de 2017, Tabla 5 del ICA). En general, manténgase informado con los avisos oficiales del SIATA y del Área Metropolitana del Valle de Aburrá. Esta es una herramienta académica, no un consejo médico personalizado.

### 11. ¿Se prevé un episodio crítico para mañana?
- **Herramientas usadas:** predict_tomorrow, search_docs (esperadas: predict_tomorrow)
- **Fuentes citadas:** poeca_acuerdo15_2016.md
- **Respuesta:** No se prevé un episodio crítico para mañana. El modelo del proyecto estima una categoría “Aceptable” con 93,3 % de probabilidad y solo un 6,7 % de “Dañina para grupos sensibles o peor” (Modelo del proyecto). Según el POECA del Área Metropolitana, los episodios críticos comienzan con alerta naranja (ICA 101–150, es decir 35,5 a 55,4 µg/m³ de PM2.5) (POECA: protocolo para episodios críticos de contaminación en el Valle de Aburrá, Niveles de contingencia por PM2.5 (Artículo 11)). La predicción se basa en datos hasta el 31 de diciembre de 2025 y no sustituye los avisos oficiales del SIATA ni del Área Metropolitana.

### 12. ¿Qué papel cumple el SIATA en el monitoreo del aire?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** siata_reporte_ica.md
- **Respuesta:** El SIATA opera estaciones de monitoreo de calidad del aire en el Valle de Aburrá y publica reportes diarios del ICA de PM2.5, que muestran el impacto real de los contaminantes en la salud de la población (Reporte diario del ICA de PM2.5 del SIATA, Estaciones de representatividad poblacional). Sus mediciones permiten identificar condiciones desfavorables para la dispersión de contaminantes cuando el ICA está en niveles rojo o naranja (Reporte diario del ICA de PM2.5 del SIATA, Estaciones de representatividad poblacional). En general, el SIATA es una entidad técnica que genera información y alertas para apoyar la toma de decisiones sobre la calidad del aire en el área metropolitana.

### 13. ¿Qué tipo de mascarilla debo usar si el aire está muy dañino?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** —
- **Respuesta:** No encontré en los documentos oficiales del Valle de Aburrá una recomendación específica de tipo de mascarilla para aire muy dañino. En general, cuando el aire está muy dañino o peligroso, lo más efectivo es reducir la exposición quedándose en interiores y evitando actividades al aire libre; si debe salir, una mascarilla bien ajustada que filtre partículas finas puede ayudar, pero no elimina todos los riesgos. Esta no es una recomendación médica personalizada. Consulte los avisos oficiales del SIATA y del Área Metropolitana del Valle de Aburrá para medidas de protección durante episodios críticos.

### 14. ¿Cuánto fue el PM2.5 en la estación Almacén General de EPM?
- **Herramientas usadas:** get_pm25 (esperadas: get_pm25)
- **Fuentes citadas:** —
- **Respuesta:** En la estación Almacén General de EPM, el último PM2.5 disponible fue de 17,05 µg/m³ el 31 de diciembre de 2025, con categoría ICA Aceptable. En los últimos 7 días los valores estuvieron entre 13,25 y 18,0 µg/m³, todos en categoría Aceptable (Datos: SISAIRE-IDEAM, estación ALMACÉN GENERAL DE EPM, del 25 al 31 de diciembre de 2025). En general, el PM2.5 mide partículas finas en el aire que pueden afectar la salud cuando se elevan. Consulta los avisos oficiales del SIATA y del Área Metropolitana si hay riesgo para la salud.

### 15. ¿Cuál es el valor máximo anual permitido de PM2.5 en Colombia?
- **Herramientas usadas:** search_docs (esperadas: search_docs)
- **Fuentes citadas:** res2254_norma_calidad_aire.md
- **Respuesta:** Según la Resolución 2254 de 2017, el valor máximo anual permitido de PM2.5 es de 25 µg/m³ como promedio anual desde el 1 de enero de 2018, y se reducirá a 15 µg/m³ a partir del 1 de enero de 2030 (Fuente: Resolución 2254 de 2017: norma de calidad del aire en Colombia, Límite diario y anual de PM2.5 (Artículo 2, Tabla 1); Meta a 2030 (Artículo 3, Tabla 2)).
