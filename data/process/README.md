# `data/process` folder

This folder contains **processed/intermediate data** and/or artifacts produced by pipelines (for example: clean datasets, features, aggregates, intermediate tables, or transformation outputs).

- **Main purpose**: clearly separate “raw” data from data ready for analysis, modeling, or app consumption.
- **Recommendation**: document which pipeline produces each artifact, its schema, refresh cadence, and how quality is validated (checks, constraints, data tests).

> _Spanish version: [README.es.md](./README.es.md)._

## `business_kpis.py`

Pure pandas transformations of the business performance pipeline (`data/pipelines/pipeline.py`), one function per transformation task: event validation against the event contract and natural-key dedupe, country of returns, KPIs as numerator and denominator, statuses, recompute window, quality signals and weekly aggregation. No database access. It is a script rather than a dataset because the pipeline brief asks for reusable transformation scripts in `data/process/`. Tests in `tests/pipelines/test_business_kpis.py` and, through the pipeline tasks, `tests/pipelines/test_pipeline.py`.

## `sales_forecast_features.py`

Pure pandas functions of the sales forecast: `load_sales` (checks `data/raw/trackflow_sales.csv` against the sales forecasting BRIEFING and handles missing values), `add_time_features` (causal lags, rolling statistics and cyclic month, plus the same values scaled by the mean of the previous 12 months) `split_train_test` (first 8 years for training, last 2 for testing, split by date) and `time_series_folds` (expanding-window cross-validation folds, equivalent to `TimeSeriesSplit` without depending on scikit-learn). Used by `scripts/train_sales_forecast.py`; tests in `tests/pipelines/test_sales_forecast.py` and `tests/pipelines/test_sales_forecast_cv.py`. Results and design in `data/eval/sales_forecast/README.md`.
