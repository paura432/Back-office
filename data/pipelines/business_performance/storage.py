"""SQL del pipeline de desempeño de negocio.

- Fuente: ``public.telemetry_events``, solo lectura, con un rol miembro de
  ``telemetry_reader``. Siempre se filtra por ventana de ``timestamp`` (y por
  ``event_type`` cuando aplica): nunca se lee la tabla entera.
- Destino: ``reporting.*``, con un rol miembro de ``reporting_writer`` (el
  pipeline) o de ``reporting_reader`` (los endpoints).

Los días son días UTC. Las fechas se pasan a SQL como medianoche UTC con zona
horaria, para no depender del ``TimeZone`` de la sesión. Ningún error incluye
el DSN.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pandas as pd
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from data.pipelines.business_performance import config
from data.process.business_kpis import SOURCE_EVENT_TYPES

CONNECT_TIMEOUT_SECONDS = 3
EVENT_COLUMNS = ["event_id", "event_type", "timestamp", "service", "tags"]


def connect(dsn: str, **kwargs) -> psycopg.Connection:
    return psycopg.connect(dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS, **kwargs)


def utc_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def _range(start: date, end: date) -> dict:
    return {"start": utc_midnight(start), "end": utc_midnight(end)}


# --- Fuente: public.telemetry_events ------------------------------------------

EXTRACT_EVENTS = """
select event_id::text as event_id, event_type, "timestamp", service, tags
from public.telemetry_events
where event_type = any(%(types)s)
  and "timestamp" >= %(start)s and "timestamp" < %(end)s
"""

# Latido por servicio y hora: distingue "cero actividad" de "no ha llegado nada".
HEARTBEAT = """
select service, date_trunc('hour', "timestamp" at time zone 'UTC') as hour, count(*)::int as events
from public.telemetry_events
where "timestamp" >= %(start)s and "timestamp" < %(end)s
group by 1, 2
"""

INSTRUMENTED_SINCE = """
select event_type, min("timestamp") as first_seen
from public.telemetry_events
where event_type = any(%(types)s)
group by event_type
"""

# Huella de cada día: detecta días ya cargados que han cambiado (§2.5).
DAY_FINGERPRINTS = """
select ("timestamp" at time zone 'UTC')::date as metric_date,
       md5(string_agg(event_id::text, ',' order by event_id)) as checksum
from public.telemetry_events
where event_type = any(%(types)s)
  and "timestamp" >= %(start)s and "timestamp" < %(end)s
group by 1
"""


def extract_source_events(dsn: str, start: date, end: date) -> pd.DataFrame:
    """Eventos de los tipos fuente con ``timestamp`` en ``[start, end)``."""
    with connect(dsn) as connection:
        rows = connection.execute(EXTRACT_EVENTS, {"types": list(SOURCE_EVENT_TYPES), **_range(start, end)}).fetchall()
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)


def producer_heartbeat(dsn: str, start: date, end: date) -> pd.DataFrame:
    """Eventos de cualquier tipo por ``service`` y hora UTC en ``[start, end)``."""
    with connect(dsn) as connection:
        rows = connection.execute(HEARTBEAT, _range(start, end)).fetchall()
    frame = pd.DataFrame(rows, columns=["service", "hour", "events"])
    frame["hour"] = pd.to_datetime(frame["hour"]).dt.tz_localize("UTC") if not frame.empty else frame["hour"]
    return frame.sort_values(["service", "hour"]).reset_index(drop=True)


def instrumented_since(dsn: str) -> dict[str, str | None]:
    """Primera aparición de cada tipo fuente (ISO 8601 en UTC) o ``None``."""
    with connect(dsn) as connection:
        found = dict(connection.execute(INSTRUMENTED_SINCE, {"types": list(SOURCE_EVENT_TYPES)}).fetchall())
    return {
        event_type: found[event_type].astimezone(timezone.utc).isoformat() if event_type in found else None
        for event_type in SOURCE_EVENT_TYPES
    }


def day_fingerprints(dsn: str, start: date, end: date) -> dict[date, str]:
    """Huella de los eventos fuente de cada día de ``[start, end)`` con eventos."""
    with connect(dsn) as connection:
        rows = connection.execute(DAY_FINGERPRINTS, {"types": list(SOURCE_EVENT_TYPES), **_range(start, end)})
        return dict(rows.fetchall())


# --- Destino: control de corridas -------------------------------------------------

LOADED_FINGERPRINTS = """
select distinct on (metric_date) metric_date, source_checksum
from reporting.pipeline_run_days
where status = 'loaded' and metric_date >= %(start)s and metric_date < %(end)s
order by metric_date, finished_at desc
"""

INSERT_RUN = """
insert into reporting.pipeline_runs
  (run_id, flow_name, trigger, requested_by, window_start, window_end, status, pipeline_version, finished_at,
   error_message)
values (%(run_id)s, %(flow_name)s, %(trigger)s, %(requested_by)s, %(window_start)s, %(window_end)s, %(status)s,
        %(pipeline_version)s, case when %(status)s = 'running' then null else now() end, %(error_message)s)
on conflict (run_id) do update
set status = excluded.status, started_at = now(), finished_at = excluded.finished_at,
    window_start = excluded.window_start, window_end = excluded.window_end, error_message = excluded.error_message
"""

# Con el candado en la mano, cualquier otra fila 'running' es de una corrida
# que murió sin cerrarse (su conexión liberó el candado al caer).
MARK_ORPHANS = """
update reporting.pipeline_runs
set status = 'crashed', finished_at = greatest(now(), started_at),
    error_message = 'Orphaned run: the pipeline lock was released without closing the run'
where status = 'running' and run_id <> %(run_id)s
returning run_id::text
"""

LOCK_HOLDER = """
select run_id::text from reporting.pipeline_runs where status = 'running' order by started_at desc limit 1
"""

FINISH_FIELDS = (
    "status", "failed_stage", "window_start", "window_end", "events_extracted", "events_deduplicated",
    "events_invalid", "rows_inserted", "rows_updated", "rows_unchanged", "rows_deleted", "late_days_detected",
    "source_max_timestamp", "error_class", "error_message",
)


def loaded_fingerprints(dsn: str, start: date, end: date) -> dict[date, str]:
    """Huella guardada la última vez que se cargó cada día de ``[start, end)``."""
    with connect(dsn) as connection:
        return dict(connection.execute(LOADED_FINGERPRINTS, {"start": start, "end": end}).fetchall())


def try_lock(connection: psycopg.Connection) -> bool:
    """Candado de sesión: se libera al cerrar la conexión, también si el
    proceso muere, así que nunca queda bloqueado."""
    return connection.execute("select pg_try_advisory_lock(%s)", (config.LOCK_KEY,)).fetchone()[0]


def lock_holder(connection: psycopg.Connection) -> str | None:
    row = connection.execute(LOCK_HOLDER).fetchone()
    return row[0] if row else None


def insert_run(connection: psycopg.Connection, **run) -> None:
    connection.execute(INSERT_RUN, {
        "flow_name": config.FLOW_NAME, "pipeline_version": config.PIPELINE_VERSION, "error_message": None, **run,
    })


def mark_orphans_crashed(connection: psycopg.Connection, run_id: str) -> list[str]:
    return [row[0] for row in connection.execute(MARK_ORPHANS, {"run_id": run_id}).fetchall()]


def finish_run(dsn: str, run_id: str, *, only_if_running: bool = False, **fields) -> None:
    """Cierra la fila de la corrida. ``last_completed_date`` sale de los días
    confirmados en ``pipeline_run_days``, así que también es correcto cuando
    la carga falla a mitad."""
    unknown = set(fields) - set(FINISH_FIELDS)
    if unknown:
        raise ValueError(f"Unknown pipeline_runs fields: {sorted(unknown)}")
    assignments = [sql.SQL("{} = {}").format(sql.Identifier(name), sql.Placeholder(name)) for name in fields]
    query = sql.SQL("""
        update reporting.pipeline_runs r
        set {assignments}, finished_at = greatest(now(), r.started_at),
            last_completed_date = (select max(d.metric_date) from reporting.pipeline_run_days d
                                   where d.run_id = r.run_id and d.status = 'loaded')
        where r.run_id = {run_id} {only_if_running}
    """).format(
        assignments=sql.SQL(", ").join(assignments),
        run_id=sql.Placeholder("run_id"),
        only_if_running=sql.SQL("and r.status = 'running'" if only_if_running else ""),
    )
    with connect(dsn) as connection:
        connection.execute(query, {**fields, "run_id": run_id})


# --- Destino: carga de KPIs -------------------------------------------------------

UPSERT_KPIS = """
insert into reporting.executive_kpis_daily as t
  (kpi, metric_date, country, carrier, currency, numerator, denominator, value, unit, status,
   source_event_count, source_checksum, pipeline_version, run_id, computed_at)
select r.kpi, r.metric_date, r.country, r.carrier, r.currency, r.numerator, r.denominator, r.value, r.unit,
       r.status, r.source_event_count, r.source_checksum, %(pipeline_version)s, %(run_id)s, now()
from jsonb_to_recordset(%(rows)s::jsonb) as r(
  kpi text, metric_date date, country text, carrier text, currency text, numerator numeric, denominator numeric,
  value numeric, unit text, status text, source_event_count integer, source_checksum text
)
on conflict (kpi, metric_date, country, carrier, currency) do update
set numerator = excluded.numerator, denominator = excluded.denominator, value = excluded.value,
    unit = excluded.unit, status = excluded.status, source_event_count = excluded.source_event_count,
    source_checksum = excluded.source_checksum, pipeline_version = excluded.pipeline_version,
    run_id = excluded.run_id, computed_at = excluded.computed_at, revision = t.revision + 1
where (t.numerator, t.denominator, t.value, t.unit, t.status, t.source_checksum, t.pipeline_version)
      is distinct from
      (excluded.numerator, excluded.denominator, excluded.value, excluded.unit, excluded.status,
       excluded.source_checksum, excluded.pipeline_version)
returning (xmax = 0) as inserted
"""

# Combinaciones del día que ya no salen en el cálculo. El trigger de
# historial guarda lo borrado con el run_id de reporting.run_id.
DELETE_OBSOLETE = """
delete from reporting.executive_kpis_daily t
where t.metric_date = %(day)s
  and not exists (
    select 1 from jsonb_to_recordset(%(rows)s::jsonb) as k(kpi text, country text, carrier text, currency text)
    where k.kpi = t.kpi and k.country = t.country and k.carrier = t.carrier and k.currency = t.currency
  )
"""

UPSERT_RUN_DAY = """
insert into reporting.pipeline_run_days
  (run_id, metric_date, status, events_extracted, events_after_dedupe, rows_written, source_checksum, quality)
values (%(run_id)s, %(metric_date)s, %(status)s, %(events_extracted)s, %(events_after_dedupe)s, %(rows_written)s,
        %(source_checksum)s, %(quality)s::jsonb)
on conflict (run_id, metric_date) do update
set status = excluded.status, events_extracted = excluded.events_extracted,
    events_after_dedupe = excluded.events_after_dedupe, rows_written = excluded.rows_written,
    source_checksum = excluded.source_checksum, quality = excluded.quality, finished_at = now()
"""


def load_day(connection: psycopg.Connection, run_id: str, day: dict, rows: list[dict], quality: dict) -> dict:
    """Carga un día en una transacción: upsert de sus filas, borrado de las
    obsoletas y fila ``loaded`` en ``pipeline_run_days``. O entra el día
    entero o no entra nada de ese día."""
    payload = json.dumps(rows)
    with connection.transaction():
        connection.execute("select set_config('reporting.run_id', %s, true)", (run_id,))
        written = connection.execute(UPSERT_KPIS, {
            "rows": payload, "run_id": run_id, "pipeline_version": config.PIPELINE_VERSION,
        }).fetchall()
        inserted = sum(1 for (is_insert,) in written if is_insert)
        deleted = connection.execute(DELETE_OBSOLETE, {"day": day["metric_date"], "rows": payload}).rowcount
        connection.execute(UPSERT_RUN_DAY, {
            "run_id": run_id, "metric_date": day["metric_date"], "status": "loaded",
            "events_extracted": day["events_extracted"], "events_after_dedupe": day["events_after_dedupe"],
            "rows_written": len(written), "source_checksum": day["source_checksum"], "quality": json.dumps(quality),
        })
    return {"inserted": inserted, "updated": len(written) - inserted, "unchanged": len(rows) - len(written),
            "deleted": deleted}


def record_failed_day(connection: psycopg.Connection, run_id: str, day: dict) -> None:
    """Deja constancia del día cuya transacción falló por un error de datos.
    Los errores de conexión no llegan aquí: no habría con qué escribir."""
    with connection.transaction():
        connection.execute(UPSERT_RUN_DAY, {
            "run_id": run_id, "metric_date": day["metric_date"], "status": "failed",
            "events_extracted": day["events_extracted"], "events_after_dedupe": day["events_after_dedupe"],
            "rows_written": 0, "source_checksum": day["source_checksum"], "quality": "{}",
        })


# --- Lecturas para los endpoints ----------------------------------------------------

RUN_COLUMNS = (
    "run_id", "flow_name", "trigger", "requested_by", "window_start", "window_end", "started_at", "finished_at",
    "status", "failed_stage", "last_completed_date", "events_extracted", "events_deduplicated", "events_invalid",
    "rows_inserted", "rows_updated", "rows_unchanged", "rows_deleted", "late_days_detected", "source_max_timestamp",
    "pipeline_version", "error_class", "error_message",
)
_RUN_SELECT = sql.SQL("select {} from reporting.pipeline_runs").format(
    sql.SQL(", ").join(sql.Identifier(column) for column in RUN_COLUMNS)
)

LATEST_KPI_DAY = """
select metric_date, max(computed_at) as computed_at,
       json_agg(json_build_object('kpi', kpi, 'country', country, 'status', status)) as statuses
from reporting.executive_kpis_daily
where metric_date = (select max(metric_date) from reporting.executive_kpis_daily)
group by metric_date
"""

RUN_DAYS = """
select metric_date, status, events_extracted, events_after_dedupe, rows_written, source_checksum, quality, finished_at
from reporting.pipeline_run_days where run_id = %(run_id)s order by metric_date
"""

KPI_ROWS = """
select kpi, metric_date, country, carrier, currency, numerator, denominator, value, unit, status, revision,
       computed_at
from reporting.executive_kpis_daily
where metric_date >= %(start)s and metric_date < %(end)s
  and (%(country)s::text is null or country = %(country)s::text)
order by metric_date, kpi, country, carrier, currency
"""


def _plain(row: dict) -> dict:
    """numeric -> float y uuid -> texto, listos para JSON."""
    return {
        key: float(value) if isinstance(value, Decimal) else str(value) if key == "run_id" and value else value
        for key, value in row.items()
    }


def _one_run(connection: psycopg.Connection, where: str, params: dict | None = None) -> dict | None:
    query = _RUN_SELECT + sql.SQL(" " + where + " order by started_at desc limit 1")
    row = connection.execute(query, params or {}).fetchone()
    return _plain(row) if row else None


def read_status(dsn: str) -> dict:
    """Última corrida, última completada, corrida activa y estado de los KPIs
    del último día calculado."""
    with connect(dsn, row_factory=dict_row) as connection:
        latest = connection.execute(LATEST_KPI_DAY).fetchone()
        return {
            "last_run": _one_run(connection, ""),
            "last_completed_run": _one_run(connection, "where status = 'completed'"),
            "active_run": _one_run(connection, "where status = 'running'"),
            "latest_metric_date": latest["metric_date"] if latest else None,
            "latest_computed_at": latest["computed_at"] if latest else None,
            "statuses": latest["statuses"] if latest else [],
        }


def read_run(dsn: str, run_id: str) -> dict | None:
    with connect(dsn, row_factory=dict_row) as connection:
        run = _one_run(connection, "where run_id = %(run_id)s", {"run_id": run_id})
        if run is None:
            return None
        run["days"] = connection.execute(RUN_DAYS, {"run_id": run_id}).fetchall()
        return run


def read_kpi_rows(dsn: str, start: date, end: date, country: str | None) -> list[dict]:
    with connect(dsn, row_factory=dict_row) as connection:
        rows = connection.execute(KPI_ROWS, {"start": start, "end": end, "country": country}).fetchall()
    return [_plain(row) for row in rows]

