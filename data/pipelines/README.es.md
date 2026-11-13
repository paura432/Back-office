# Carpeta `data/pipelines`

Esta carpeta agrupa **todos los pipelines de datos del monorepo** relacionados con la compañía: procesos de ingesta, ETL/ELT, limpieza, transformación y carga hacia sistemas analíticos o de producción.

Cada subcarpeta o archivo dentro de `data/pipelines/` debe representar **un pipeline o conjunto de jobs** (por ejemplo `sales-etl`, `telemetry-stream`, `customer-segmentation`) e incluir la configuración necesaria (scripts, orquestación, conectores, esquemas, etc.).

- **Propósito principal**: unificar en un único lugar la lógica de movimiento y transformación de datos que soporta las aplicaciones y analíticas de la compañía.
- **Recomendación**: documenta aquí los pipelines que vayas añadiendo, describiendo su objetivo, orígenes/destinos de datos, dependencias y cómo ejecutarlos en desarrollo, pruebas y producción.

## `business_performance` — pipeline de desempeño de negocio

Calcula cada día, a partir de `public.telemetry_events`, los KPIs del informe ejecutivo (volumen de envíos, entregas a tiempo, coste de transporte, devoluciones y satisfacción, por país) y los guarda en `reporting.executive_kpis_daily` (nombre provisional: falta el BRIEFING). El diseño está en [`PIPELINE_DESIGN.md`](PIPELINE_DESIGN.md); la §9 resume cómo se ha implementado.

```text
data/pipelines/
  pipeline.py                     flow business_performance_flow, sus tasks y la línea de comandos
  business_performance/
    config.py                     parámetros no secretos: ventanas, cron, países, candado
    storage.py                    SQL de la fuente (telemetry_events) y del destino (reporting.*)
    entrypoints.py                lo único que importa services/reporting
    synthetic.py                  eventos de negocio sintéticos para telemetry_test
  tests/                          transformación pura y flow completo contra telemetry_test
  pyproject.toml, uv.lock         Prefect 3.4.5, pandas 3.1.1, psycopg 3.2.6
data/process/business_kpis.py     transformaciones pandas puras
data/raw/business_performance/    eventos sintéticos generados (no se versionan)
data/eval/business_performance/   resumen JSON de cada corrida (runs/, no se versiona) y evidencias
```

### Base de datos y variables

La migración `services/api/supabase/migrations/20261106193654_create_reporting_schema.sql` crea el esquema `reporting` y los roles de grupo `reporting_writer` y `reporting_reader`. Con el Supabase local en marcha (`services/api/README.md`):

```sh
npx supabase migration up --local --workdir services/api
docker exec -i supabase_db_trackflow-back-office psql -U postgres -d postgres \
  -c "create role trackflow_pipeline_local login password '<local password>' in role telemetry_reader, reporting_writer" \
  -c "create role trackflow_reporting_local login password '<local password>' in role reporting_reader"
```

| Variable | Rol de login | Para qué |
|---|---|---|
| `BUSINESS_PERFORMANCE_SOURCE_DSN` | miembro de `telemetry_reader` | Leer `telemetry_events`. Si no está, se usa el bloque `Secret` `business-performance-source-dsn` |
| `BUSINESS_PERFORMANCE_REPORTING_DSN` | miembro de `reporting_writer` | Escribir en `reporting`. Si no está, bloque `Secret` `business-performance-reporting-dsn` |
| `PREFECT_API_URL` | — | Servidor de Prefect. Sin ella, `pipeline.py` arranca uno temporal para esa corrida |
| `BUSINESS_PERFORMANCE_EVAL_DIR` | — | Carpeta del resumen de cada corrida (por defecto `data/eval/business_performance/runs`) |

### Ejecución

Desde la raíz del repositorio:

```sh
uv sync --project data/pipelines --frozen
uv run --project data/pipelines python data/pipelines/pipeline.py                         # últimos 7 días + días tardíos
uv run --project data/pipelines python data/pipelines/pipeline.py --start 2026-10-01 --end 2026-10-08
```

Con el entorno activado (`source data/pipelines/.venv/bin/activate`) vale `python data/pipelines/pipeline.py`. Termina con código 0 y el resumen de la corrida en JSON, o con código 1 si la corrida falla o se salta.

**Frecuencia:** diaria a las 04:00 UTC (deployment `business-performance-daily`, una corrida a la vez y las demás en cola). El informe ejecutivo es semanal (lunes a las 07:00) y lee los 7 días anteriores. Para servir el deployment, que también ejecuta los disparos de `POST /reporting/pipeline/runs`:

```sh
uv run --project data/pipelines prefect server start --host 127.0.0.1 --port 4200
PREFECT_API_URL=http://127.0.0.1:4200/api uv run --project data/pipelines python data/pipelines/pipeline.py --serve
```

### Datos de prueba

Ningún evento fuente de estos KPIs se emite todavía: con los datos reales todos los KPIs salen `not_instrumented`. Para probar con datos se generan eventos sintéticos (deterministas e idempotentes) que solo se insertan en una base llamada `telemetry_test`:

```sh
uv run --project data/pipelines python -m data.pipelines.business_performance.synthetic \
  --start 2026-10-24 --end 2026-11-06 --dsn-env REPORTING_TEST_ADMIN_DSN \
  --jsonl data/raw/business_performance/synthetic_events.jsonl
```

### Tests

```sh
cd data/pipelines && uv run --frozen --extra dev pytest
```

Los tests del flow (`tests/test_pipeline_flow.py`) necesitan `REPORTING_TEST_PIPELINE_DSN` (login con `telemetry_reader` y `reporting_writer`) y `REPORTING_TEST_ADMIN_DSN` (rol con BYPASSRLS) sobre `telemetry_test` con las migraciones aplicadas; si no están, se saltan.

### Versiones

Prefect 3.4.5 es la versión más reciente compatible con `fastapi==0.115.12`, que fija `services/api` (la API usa `prefect-client` de la misma versión para disparar el deployment). `pyproject.toml` limita además `pydantic-settings`, FastAPI y SQLAlchemy, con los que Prefect 3.4.5 avisa o deja de funcionar (el scheduler no crea las corridas del cron con SQLAlchemy 2.1).
