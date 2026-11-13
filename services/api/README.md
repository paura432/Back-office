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
`{"received": N, "stored": N, "rejected": N}`. Each event is validated on its
own with `TypeAdapter(TelemetryEvent)`, built from
`app/schemas/event-schemas.json` (a copy of `docs/telemetry/event-schemas.json`
kept identical by `tests/test_telemetry.py`). Invalid events are rejected one by
one and the valid ones are written to Supabase `public.telemetry_events` in a
single insert. Already stored or repeated `eventId`s are skipped and count only
in `received`. A malformed batch gets 422; a storage failure gets 503 and
nothing is stored. Details in `docs/telemetry/storage.md`.

A successful `POST /inventory/movements` also emits the business event
`inventory_movement_recorded` (`sku`, `warehouse`, `quantity_delta`,
`quantity_after`) after the response is sent. Its `requestId` is the request's
`X-Request-Id` when it is a valid UUID, otherwise a new one. Rejected movements
(404, 409, 422) emit nothing. If the event cannot be stored (missing
`TELEMETRY_DATABASE_DSN`, database down) the movement is unaffected, a
`telemetry_emit_failed` warning is logged and the event is dropped without retry.

`GET /telemetry/report?start_date=…&end_date=…` returns the technical telemetry
report: events per day, frontend error rate per day, frontend errors by route
and kind, and Web Vitals per day. Both dates are optional ISO 8601 values
(default: the last 7 days, UTC). The metrics are pandas functions in
`app/telemetry/analysis.py`; the endpoint resolves the period once, passes it to
each metric and caches the result for 60 s per date combination. Details in
`docs/telemetry/report.md`.

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

## Telemetry storage (local Supabase)

The migration lives in `supabase/migrations/`. With Docker and the Supabase CLI
(`npx supabase@2.122.0`), from this folder:

```sh
npx supabase start --workdir . -x studio,storage-api,imgproxy,realtime,edge-runtime,logflare,vector,mailpit,postgres-meta,supavisor
```

`start` applies the migration to the local database (port 54322). The table is
only writable through the `telemetry_writer` group role, so create a login role
for the API with a password of your own (never commit it):

```sh
docker exec -i supabase_db_trackflow-back-office psql -U postgres -d postgres \
  -c "create role trackflow_api_local login password '<local password>' in role telemetry_writer"
```

Then run the API with
`TELEMETRY_DATABASE_DSN=postgresql://trackflow_api_local:<local password>@127.0.0.1:54322/postgres`.
Without it the endpoint answers 503. The Compose `api` service does not set this
variable yet.

`tests/test_telemetry_storage.py` runs against a real database only when
`TELEMETRY_TEST_DATABASE_DSN` (login role with `telemetry_writer`) and
`TELEMETRY_TEST_ADMIN_DSN` (table owner) are set; otherwise it is skipped. Point
them at a separate development/test database with the migration applied: rows
cannot be deleted.

## Telemetry report

`GET /telemetry/report` reads `public.telemetry_events` through
`TELEMETRY_READ_DATABASE_DSN`, a login role granted `telemetry_reader` (SELECT
only, migration `20261106183444_create_telemetry_reader.sql`). The writer role
still cannot read. Apply pending migrations without resetting the local
database, then create the reader login role with a password of your own (never
commit it):

```sh
npx supabase migration up --local --workdir .
docker exec -i supabase_db_trackflow-back-office psql -U postgres -d postgres \
  -c "create role trackflow_report_local login password '<local password>' in role telemetry_reader"
```

Run the API with
`TELEMETRY_READ_DATABASE_DSN=postgresql://trackflow_report_local:<local password>@127.0.0.1:54322/postgres`.
Without it the report answers 503. The Compose `api` service does not set this
variable yet.

`tests/test_telemetry_report_storage.py` also needs `TELEMETRY_TEST_READER_DSN`
(login role with `telemetry_reader` on the test database), besides the two
variables above; otherwise it is skipped.

## Business performance reporting

`main.py` mounts the `/reporting` router from `services/reporting/`, which
imports `data/pipelines/business_performance/entrypoints.py`. Neither lives in
this folder, so the repository root must be importable: `PYTHONPATH=../..` when
running locally (pytest already adds it), and Compose mounts `services/reporting`
and `data` read-only under `/repo` with `PYTHONPATH=/repo`. Details in
`services/reporting/README.md`.

Migration `20261106193654_create_reporting_schema.sql` creates the `reporting`
schema. The endpoints read it with `REPORTING_READ_DATABASE_DSN`, a login role
granted `reporting_reader` (SELECT only):

```sh
npx supabase migration up --local --workdir .
docker exec -i supabase_db_trackflow-back-office psql -U postgres -d postgres \
  -c "create role trackflow_reporting_local login password '<local password>' in role reporting_reader"
```

`POST /reporting/pipeline/runs` also needs `PREFECT_API_URL` and
`APP_ENV=development` or `test`. Without the DSN or Prefect the endpoints answer
503; the Compose `api` service sets neither yet. `tests/test_reporting.py` runs
its database tests only when `REPORTING_TEST_PIPELINE_DSN` (login role with
`reporting_writer`) and `REPORTING_TEST_READER_DSN` (login role with
`reporting_reader`) point at the test database.

## Local Development

Requires Python 3.12 and uv 0.6.17 or compatible newer version:

```sh
uv sync --frozen
PYTHONPATH=../.. uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Runtime and testing dependencies, including transitive packages and hashes, are
recorded in `uv.lock`. Install tests with `uv sync --frozen --extra dev` and run
them with `uv run --frozen --extra dev pytest -q`. To intentionally update a
dependency, edit `pyproject.toml` and run the pinned project uv version's
`uv lock`.

## Docker Development

From the repository root, run `docker compose up --build -d`. Compose installs
locked dependencies automatically, mounts this directory (plus `services/reporting`
and `data` read-only under `/repo`) and runs Uvicorn with `--reload`. The virtual environment is outside the bind mount at `/opt/venv`.

The service is available internally at `http://api:8000/health` and locally at
`http://localhost:8000/health`. Browser clients use `/api/health` on either Next.js
frontend; Next.js rewrites proxy to the API and strip `/api`.