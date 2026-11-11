# Datos y modelo de este proyecto

Fuente: documentación del proyecto (repositorio si3003-calidad-aire, README y src/datos/procesar.py).

## De dónde vienen los datos

Las mediciones provienen del conjunto "Calidad del Aire en Colombia" de datos.gov.co (identificador g4t8-zkc3, Subsistema de Información sobre Calidad del Aire, SISAIRE, del IDEAM), filtrado a las estaciones del Área Metropolitana del Valle de Aburrá. Son mediciones horarias de PM2.5, lluvia, velocidad del viento y temperatura entre 2020 y 2025. El último día disponible es el 31 de diciembre de 2025, así que el sistema no muestra mediciones en tiempo real.

## Control de calidad

Entre 2020 y 2023 muchas estaciones publican PM2.5, viento y lluvia con valores multiplicados por 10 o 100. El proyecto no corrige esos valores: descarta los meses de cada estación cuya distribución no es físicamente plausible y solo calcula un promedio diario si hay al menos 18 horas con dato. Por eso algunas estaciones no tienen datos en ciertos años.

## Qué predice el modelo

La herramienta de predicción usa el modelo clásico de la Parte 1 del proyecto, entrenado con los datos procesados. Predice la categoría de calidad del aire del día siguiente para el promedio del valle en tres clases: Buena (PM2.5 menor de 12,5 µg/m³), Aceptable (de 12,5 a 37,4 µg/m³) y Dañina para grupos sensibles o peor (37,5 µg/m³ o más). Se compara con una línea base de persistencia, que supone que mañana tendrá la misma categoría que hoy.

## Limitaciones

Los días dañinos son pocos (menos del 2 % de los días-estación), así que el modelo tiene poca experiencia con episodios críticos. La predicción es para el promedio del valle, no para una estación específica. Este sistema es una herramienta académica: no reemplaza los avisos oficiales del SIATA y del Área Metropolitana ni constituye consejo médico.
