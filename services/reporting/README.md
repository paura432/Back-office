# `services/reporting`

Endpoints of the business performance pipeline (`data/pipelines/PIPELINE_DESIGN.md`, section 5.2), kept apart from `/telemetry`. The router only validates requests and maps errors to HTTP; SQL, KPI rules and the Prefect trigger live in `data/pipelines/business_performance/entrypoints.py`. `services/` imports from `data/`, never the other way round.

It is mounted by `services/api/main.py`, so it shares the API conventions: Pydantic `response_model` on every route, errors as `{"detail": ...}`, 422 for invalid parameters and 503 when storage is unavailable. There is no authentication yet (auth routes are 501 stubs); the manual trigger is only enabled with `APP_ENV` `development` or `test`, like the inventory demo.

| Endpoint | Response |
|---|---|
| `GET /reporting/pipeline/status` | Last run and last completed run (status, window, start and end time, events processed, sanitized error), run still marked as running, data freshness and status of each KPI and country on the latest computed day |
| `POST /reporting/pipeline/runs` | Body `{"window_start", "window_end", "requested_by"}`, all optional. Schedules a run of the `business-performance-daily` deployment with `run_deployment(timeout=0)`: `202 {"run_id", "status": "scheduled"}`. 409 with the active `run_id` if a run is pending, running or waiting for its slot; 422 for an invalid window (both dates or none, at most 90 days); 404 outside development/test; 503 if Prefect or the deployment are unavailable |
| `GET /reporting/pipeline/runs/{run_id}` | One run with its per-day checkpoint and quality signals |
| `GET /reporting/kpis?start_date&end_date&granularity=day\|week&country=US\|ES\|all` | KPI rows of `reporting.executive_kpis_daily` (provisional name). `day` returns rows as stored (per carrier and currency); `week` aggregates per ISO week, country and currency as sum(numerator) / sum(denominator). Every row carries `status`, `revision` and `computed_at`; `value` is null when the KPI cannot be measured. Default period: the last 28 full days, at most 366 |

Configuration: `REPORTING_READ_DATABASE_DSN` (login role granted `reporting_reader`), `PREFECT_API_URL` and `APP_ENV`. Setup and tests are described in `services/api/README.md`.
