# Carpeta `data/process`

Esta carpeta contiene **datos procesados/intermedios** y/o artefactos derivados de los pipelines (por ejemplo: datasets limpios, features, agregados, tablas intermedias o resultados de transformaciones).

- **Propósito principal**: separar claramente los datos “raw” de los datos listos para análisis/modelado/consumo por apps.
- **Recomendación**: documenta qué pipeline genera cada artefacto, su esquema, periodicidad, y cómo se valida su calidad (checks, constraints, tests de datos).

## `business_kpis.py`

Transformaciones pandas puras del pipeline de desempeño de negocio (`data/pipelines/pipeline.py`), una función por cada task de transformación: validación de los eventos contra el contrato, deduplicación por clave natural, país de las devoluciones, KPIs como numerador y denominador, estados (`ok`, `no_activity`, `capture_gap`, `not_instrumented`), ventana de recálculo, señales de calidad y agregado semanal. No leen ni escriben en ninguna base de datos. Se ha puesto aquí, y no un dataset, porque el enunciado del pipeline pide guardar en `data/process/` los scripts de transformación reutilizables. Tests en `tests/pipelines/test_business_kpis.py` y, a través de las tasks del pipeline, en `tests/pipelines/test_pipeline.py`.
