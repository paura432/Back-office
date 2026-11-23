# Carpeta `data/process`

Esta carpeta contiene **datos procesados/intermedios** y/o artefactos derivados de los pipelines (por ejemplo: datasets limpios, features, agregados, tablas intermedias o resultados de transformaciones).

- **Propósito principal**: separar claramente los datos “raw” de los datos listos para análisis/modelado/consumo por apps.
- **Recomendación**: documenta qué pipeline genera cada artefacto, su esquema, periodicidad, y cómo se valida su calidad (checks, constraints, tests de datos).

## `business_kpis.py`

Transformaciones pandas puras del pipeline de desempeño de negocio (`data/pipelines/pipeline.py`), una función por cada task de transformación: validación de los eventos contra el contrato, deduplicación por clave natural, país de las devoluciones, KPIs como numerador y denominador, estados (`ok`, `no_activity`, `capture_gap`, `not_instrumented`), ventana de recálculo, señales de calidad y agregado semanal. No leen ni escriben en ninguna base de datos. Se ha puesto aquí, y no un dataset, porque el enunciado del pipeline pide guardar en `data/process/` los scripts de transformación reutilizables. Tests en `tests/pipelines/test_business_kpis.py` y, a través de las tasks del pipeline, en `tests/pipelines/test_pipeline.py`.

## `sales_forecast_features.py`

Funciones pandas puras del pronóstico de ventas: `load_sales` (comprueba `data/raw/trackflow_sales.csv` contra el BRIEFING de sales forecasting y trata los nulos), `add_time_features` (lags, estadísticas rodantes y mes cíclico calculados de forma causal, más esos mismos valores escalados por la media de los 12 meses anteriores) `split_train_test` (primeros 8 años para entrenar y últimos 2 para probar, con corte por fecha) y `time_series_folds` (folds de validación cruzada con ventana creciente, equivalentes a `TimeSeriesSplit` sin depender de scikit-learn). Las usa `scripts/train_sales_forecast.py`; tests en `tests/pipelines/test_sales_forecast.py` y `tests/pipelines/test_sales_forecast_cv.py`. Resultados y diseño en `data/eval/sales_forecast/README.md`.
