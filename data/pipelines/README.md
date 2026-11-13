# `data/pipelines` folder

This folder groups **all data pipelines in the monorepo** related to the company: ingestion, ETL/ELT, cleaning, transformation, and loading into analytical or production systems.

Each subfolder or file under `data/pipelines/` should represent **one pipeline or job set** (for example `sales-etl`, `telemetry-stream`, `customer-segmentation`) and include the required configuration (scripts, orchestration, connectors, schemas, etc.).

- **Main purpose**: consolidate in one place the data movement and transformation logic that powers the company’s applications and analytics.
- **Recommendation**: document pipelines as you add them—their goal, data sources and sinks, dependencies, and how to run them in development, testing, and production.

> _Spanish version: [README.es.md](./README.es.md)._

## `business_performance` — business performance pipeline

Computes the executive report KPIs (shipments, on-time deliveries, shipping cost, returns and customer satisfaction, per country) every day from `public.telemetry_events` and stores them in `reporting.executive_kpis_daily` (provisional name until the BRIEFING exists). Design and implementation notes: [`PIPELINE_DESIGN.md`](PIPELINE_DESIGN.md) (section 9; section 10 covers the subflows, the tests and the `/reporting` dashboard in the backoffice). The full guide (database roles, variables, synthetic data, tests and versions) is in [README.es.md](./README.es.md).

```sh
uv sync --project data/pipelines --frozen
uv run --project data/pipelines python data/pipelines/pipeline.py                         # last 7 days + late days
uv run --project data/pipelines python data/pipelines/pipeline.py --start 2026-10-01 --end 2026-10-08
PREFECT_API_URL=http://127.0.0.1:4200/api uv run --project data/pipelines python data/pipelines/pipeline.py --serve
```

`business_performance_flow` coordinates five subflows: `extract_executive_kpi_events`, `compute_executive_kpis` (one task per KPI), `check_executive_kpi_quality` (optional), `load_executive_kpis_daily` and `export_executive_kpi_snapshot` (optional). Tests live in `tests/pipelines/` at the repository root:

```sh
uv run --project data/pipelines python -m pytest tests/pipelines/test_pipeline.py   # task unit tests, no database
```

Schedule: daily at 04:00 UTC (`business-performance-daily` deployment, one run at a time). Variables: `BUSINESS_PERFORMANCE_SOURCE_DSN` (login role in `telemetry_reader`), `BUSINESS_PERFORMANCE_REPORTING_DSN` (login role in `reporting_writer`) and, for deployments, `PREFECT_API_URL`.
