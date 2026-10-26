# TrackFlow Development API

FastAPI service for the development stack. `GET /health` returns
`{"status":"ok"}`. `GET /status` checks PostgreSQL with `SELECT 1` and returns
`operational` or `degraded` without exposing connection details. The declared
business and authentication routes remain explicit `501 Not Implemented` stubs;
they do not implement business behavior or authentication/authorization.

`GET /inventory/items` and `GET /inventory/alerts` are local-development
exceptions: they read the synthetic PostgreSQL inventory described below.
Inventory stock is derived from signed rows in an append-only movements table;
the API does not expose a manual quantity edit. `POST /inventory/movements`
records a stock delta. Reads are held in a process-local 30-second TTL cache
whose keys include read type and all active filters; successful movements clear
both item and alert entries. This cache is not shared across API workers and
the TTL is the fallback for external/local SQL changes.

`POST /telemetry/events` accepts `{"events": [...]}` (up to 100) and returns
`{"received": N}`. Events are validated with Pydantic models generated from
`app/schemas/event-schemas.json`, a copy of `docs/telemetry/event-schemas.json`
kept identical by `tests/test_telemetry.py`. Any invalid event rejects the whole
batch with 422. There is no event store yet: accepted events are only logged
through the `trackflow.telemetry` logger.

### Synthetic inventory (local only)

The API refuses inventory database connections unless the DSN targets the
database named `trackflow` on `db`, `localhost`, `127.0.0.1`, or `::1`. The
provided Compose stack uses the local PostgreSQL service; do not point this
demo/seeder at a production or other remote database.

From the repository root (the `db` port is not published to the host, so run
it inside the `api` container):

```sh
docker compose up --build -d --wait db api
docker compose exec api python seed_inventory.py
```

The seeder is reproducible/idempotent for its fixed fictional SKUs and
warehouse quantities: it upserts movements tagged with a stable `seed_key` and
never deletes rows. If a demo item pair already has untagged movements (for
example from `POST /inventory/movements`), it refuses to run without changing
anything; recreate the local database to return to the canonical dataset.
The HTTP API itself creates the two demo tables on first inventory access.

Inventory routes:

- `GET /inventory/items?warehouse=los-angeles&sku=DEMO-BOX-001&q=box`
- `GET /inventory/alerts?warehouse=zaragoza`
- `GET /inventory/items/{sku}?warehouse=los-angeles`
- `POST /inventory/movements` with `{"sku":"DEMO-BOX-001","warehouse":"los-angeles","quantity_delta":-1}`

`services/api/bench_inventory.py` compares cold (cache-cleared) and warm
responses over the exact same seeded local dataset and emits latency percentiles
as JSON. Run it after the seeder with `docker compose exec api python
bench_inventory.py`; do not substitute synthetic numbers for a missing local
run. Recorded results are in `CACHING_REPORT.md` and `audit/caching/`.

## Local Development

Requires Python 3.12 and uv 0.6.17 or compatible newer version:

```sh
uv sync --frozen
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Runtime and testing dependencies, including transitive packages and hashes, are
recorded in `uv.lock`. Install tests with `uv sync --frozen --extra dev` and run
them with `uv run --frozen --extra dev pytest -q`. To intentionally update a
dependency, edit `pyproject.toml` and run the pinned project uv version's
`uv lock`.

## Docker Development

From the repository root, run `docker compose up --build -d`. Compose installs
locked dependencies automatically, mounts this directory and runs Uvicorn with
`--reload`. The virtual environment is outside the bind mount at `/opt/venv`.

The service is available internally at `http://api:8000/health` and locally at
`http://localhost:8000/health`. Browser clients use `/api/health` on either Next.js
frontend; Next.js rewrites proxy to the API and strip `/api`.