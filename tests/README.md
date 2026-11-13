# `tests/` — cross-cutting tests

Tests that live at the root of the monorepo instead of next to a single app or service.

## `tests/pipelines/`

Tests of the business performance pipeline (`data/pipelines/pipeline.py` and `data/process/business_kpis.py`). They run with the pipeline environment, from the repository root:

```sh
uv sync --project data/pipelines --frozen --extra dev
uv run --project data/pipelines python -m pytest tests/pipelines/test_pipeline.py   # task unit tests
uv run --project data/pipelines python -m pytest tests/pipelines                    # all pipeline tests
```

| File | What it covers | Needs a database |
|---|---|---|
| `test_pipeline.py` | Transformation tasks called directly (`task.fn`) with in-memory events: KPI values worked out by hand, inputs that break the event contract, cache key | No |
| `test_business_kpis.py` | Pure functions: dedupe, currencies, statuses, recompute window, quality signals, weekly aggregate | No |
| `test_subflows.py` | Subflows run on their own on a temporary Prefect server | No |
| `test_pipeline_flow.py` | Full flow against `telemetry_test` (skipped without `REPORTING_TEST_*_DSN`) | Yes |

`kpi_events.py` builds the in-memory events: rows shaped like `public.telemetry_events` whose `tags` follow `docs/telemetry/event-schemas.json`. Details: `data/pipelines/PIPELINE_DESIGN.md` §10.2.
