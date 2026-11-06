"""Pipeline de desempeño de negocio de TrackFlow (Parte 2 de 3).

Lee ``public.telemetry_events`` (solo lectura), calcula los KPIs del informe
ejecutivo y los carga en ``reporting.executive_kpis_daily`` (nombre
provisional hasta tener el BRIEFING). Diseño en
``data/pipelines/PIPELINE_DESIGN.md``; no toca ``telemetry_events`` ni
``services/api/app/telemetry/analysis.py``.

Ejecución, desde la raíz del repositorio y con las variables de entorno de
``data/pipelines/README.md`` (los DSN también pueden venir de bloques
``Secret`` de Prefect):

    uv run --project data/pipelines python data/pipelines/pipeline.py
        Últimos 7 días completos más los días con eventos tardíos.
    uv run --project data/pipelines python data/pipelines/pipeline.py --start 2026-10-01 --end 2026-10-08
        Ventana explícita [start, end), como mucho 90 días.
    uv run --project data/pipelines python data/pipelines/pipeline.py --serve
        Registra el deployment ``business-performance-daily`` y ejecuta sus
        corridas: las del cron y las que dispara POST /reporting/pipeline/runs.
        Necesita un servidor de Prefect (PREFECT_API_URL).

Con el entorno ya activado, ``python data/pipelines/pipeline.py`` es lo mismo.

Frecuencia: diaria a las 04:00 UTC (``config.DEPLOYMENT_CRON``). El informe
ejecutivo es semanal, los lunes a las 07:00, y lee los 7 días anteriores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # ejecutado como script, sys.path[0] es data/pipelines
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import psycopg  # noqa: E402
from prefect import flow, get_run_logger, serve, task  # noqa: E402
from prefect.blocks.system import Secret  # noqa: E402
from prefect.cache_policies import NO_CACHE  # noqa: E402
from prefect.client.schemas.objects import ConcurrencyLimitConfig, ConcurrencyLimitStrategy  # noqa: E402
from prefect.logging import get_logger  # noqa: E402
from prefect.runtime import flow_run  # noqa: E402
from prefect.schedules import Cron  # noqa: E402
from prefect.states import Cancelled  # noqa: E402

from data.pipelines.business_performance import config, storage  # noqa: E402
from data.process import business_kpis  # noqa: E402

FAILED_STAGES = ("extract", "transform", "quality", "load")


# --- Configuración ----------------------------------------------------------------


def _dsn(env_name: str, block_name: str) -> str:
    """Variable de entorno o, si no está, bloque ``Secret`` de Prefect (§4.4)."""
    value = os.environ.get(env_name)
    if value:
        return value
    try:
        return Secret.load(block_name).get()
    except Exception as exc:  # bloque inexistente o sin servidor de Prefect
        raise RuntimeError(f"Set {env_name} or create the Prefect Secret block '{block_name}'") from exc


def source_dsn() -> str:
    """Rol de login miembro de ``telemetry_reader``."""
    return _dsn(config.SOURCE_DSN_ENV, config.SOURCE_DSN_BLOCK)


def reporting_dsn() -> str:
    """Rol de login miembro de ``reporting_writer``."""
    return _dsn(config.REPORTING_DSN_ENV, config.REPORTING_DSN_BLOCK)


def _safe_message(exc: BaseException) -> str:
    """Mensaje para ``pipeline_runs.error_message``. De los errores de
    psycopg solo guardamos clase y SQLSTATE: su texto puede llevar host,
    puerto y usuario de la conexión."""
    if isinstance(exc, psycopg.Error):
        return f"{type(exc).__name__} (sqlstate {exc.sqlstate or 'n/a'})"
    return str(exc)[:500]


# --- Reintentos ------------------------------------------------------------------

# Tasks que hablan con la base de datos (Supabase): 3 reintentos con esperas
# de 10 s, 1 min y 5 min. Cubren un reinicio de Postgres o un corte del pooler
# de unos 6 minutos sin que nadie intervenga. No ponemos más porque, mientras
# espera, la corrida ocupa el único hueco del deployment, y si la caída dura
# más la siguiente corrida (cron o manual) recalcula la misma ventana sin
# duplicar nada (§3.1).
DB_RETRIES = 3
DB_RETRY_DELAYS = [10, 60, 300]


def is_transient_db_error(task, task_run, state) -> bool:
    """Solo se reintentan los errores de conexión (``OperationalError``). Un
    error de datos, de permisos o de código daría lo mismo en el siguiente
    intento."""
    try:
        state.result()
    except psycopg.OperationalError:
        return True
    except Exception:
        return False
    return False


# Ninguna task con acceso a la base de datos se cachea: una reejecución tiene
# que volver a leer la fuente porque pueden haber llegado eventos tardíos.
DB_TASK = {
    "retries": DB_RETRIES,
    "retry_delay_seconds": DB_RETRY_DELAYS,
    "retry_condition_fn": is_transient_db_error,
    "cache_policy": NO_CACHE,
}


# --- Tasks -----------------------------------------------------------------------


@dataclass
class RunHandle:
    run_id: str
    connection: psycopg.Connection | None  # conexión de control que mantiene el candado
    lock_holder: str | None = None


@task(name="register_run", **DB_TASK)
def register_run(
    run_id: str, trigger: str, requested_by: str | None, window_start: date, window_end: date
) -> RunHandle:
    """Toma el candado del pipeline y registra la corrida como ``running``.
    Si otra corrida lo tiene, registra esta como ``skipped`` y devuelve un
    handle sin conexión."""
    logger = get_run_logger()
    connection = storage.connect(reporting_dsn(), autocommit=True)
    try:
        run = {"run_id": run_id, "trigger": trigger, "requested_by": requested_by,
               "window_start": window_start, "window_end": window_end}
        if not storage.try_lock(connection):
            holder = storage.lock_holder(connection)
            storage.insert_run(connection, **run, status="skipped",
                               error_message=f"Pipeline lock held by run {holder or 'unknown'}")
            connection.close()
            return RunHandle(run_id, None, holder)
        orphans = storage.mark_orphans_crashed(connection, run_id)
        if orphans:
            logger.warning("Marked %d orphaned run(s) as crashed: %s", len(orphans), ", ".join(orphans))
        storage.insert_run(connection, **run, status="running")
        return RunHandle(run_id, connection)
    except BaseException:
        connection.close()  # libera el candado antes de reintentar
        raise


@task(name="detect_changed_days", **DB_TASK)
def detect_changed_days(today: date) -> dict:
    """Compara la huella de los últimos 35 días con la que se cargó y amplía
    la ventana de 7 días hasta el primer día que ha cambiado (§2.5)."""
    audit_start = today - timedelta(days=config.AUDIT_DAYS)
    current = storage.day_fingerprints(source_dsn(), audit_start, today)
    stored = storage.loaded_fingerprints(reporting_dsn(), audit_start, today)
    plan = business_kpis.plan_window(current, stored, today, config.AUDIT_DAYS, config.DEFAULT_WINDOW_DAYS)
    get_run_logger().info(
        "Window %s..%s, %d changed day(s), %d late day(s)",
        plan["window_start"], plan["window_end"], len(plan["changed_days"]), plan["late_days"],
    )
    return plan


@task(name="extract_events", **DB_TASK)
def extract_events(window_start: date, window_end: date) -> dict:
    """Lectura de §2.3: eventos fuente desde 30 días antes de la ventana (para
    deduplicar), latido de los productores en la ventana y primera aparición
    de cada tipo fuente."""
    dsn = source_dsn()
    events = storage.extract_source_events(
        dsn, window_start - timedelta(days=config.DEDUPE_LOOKBACK_DAYS), window_end
    )
    get_run_logger().info("Extracted %d source event(s) for %s..%s", len(events), window_start, window_end)
    return {
        "events": events,
        "heartbeat": storage.producer_heartbeat(dsn, window_start, window_end),
        "instrumented_since": storage.instrumented_since(dsn),
    }


TRANSFORM_CODE_HASH = hashlib.sha256(Path(business_kpis.__file__).read_bytes()).hexdigest()


def transform_cache_key(context, parameters: dict) -> str:
    """Clave de caché de ``transform_kpis``: un hash de todo lo que decide su
    salida, y de nada más.

    - Los eventos de entrada, por sus ``event_id``. ``telemetry_events`` es
      append-only (los triggers bloquean UPDATE y DELETE), así que el mismo
      conjunto de ``event_id`` es siempre el mismo contenido. Un evento tardío
      o un duplicado nuevo cambia la clave y obliga a recalcular.
    - El latido de los productores y la primera aparición de cada tipo
      fuente, que deciden ``no_activity``, ``capture_gap`` y
      ``not_instrumented``.
    - La ventana, los países esperados y el código de
      ``data/process/business_kpis.py``: un cambio de lógica invalida la caché
      sin tener que acordarse de subir ninguna versión.
    """
    digest = hashlib.sha256()
    digest.update(f"{TRANSFORM_CODE_HASH}|{parameters['window_start']}|{parameters['window_end']}|"
                  f"{','.join(config.EXPECTED_COUNTRIES)}".encode())
    digest.update(",".join(sorted(parameters["events"]["event_id"].astype(str))).encode())
    digest.update(parameters["heartbeat"].to_csv(index=False).encode())
    digest.update(json.dumps(parameters["instrumented_since"], sort_keys=True).encode())
    return f"business-performance-transform-{digest.hexdigest()}"


@task(
    name="transform_kpis",
    retries=0,
    cache_key_fn=transform_cache_key,
    # Válida 1 hora: si la transformación ya corrió bien en la última hora con
    # exactamente los mismos datos, no se repite (reintento de una corrida
    # cuya carga falló, disparo manual justo después del cron). Pasada la hora
    # se recalcula aunque nada haya cambiado: es barato y evita arrastrar un
    # resultado guardado indefinidamente.
    cache_expiration=timedelta(hours=1),
)
def transform_kpis(
    events: pd.DataFrame,
    heartbeat: pd.DataFrame,
    instrumented_since: dict,
    window_start: date,
    window_end: date,
) -> dict:
    """UTC -> ``metric_date``, dedupe, país, KPIs y estados (§4.2). Función
    pura: sin reintentos, porque un error determinista no se arregla
    repitiendo."""
    return business_kpis.compute_kpis(
        events, heartbeat, instrumented_since, window_start, window_end, config.EXPECTED_COUNTRIES
    )


@task(name="check_quality", retries=0, cache_policy=NO_CACHE)
def check_quality(
    events: pd.DataFrame,
    heartbeat: pd.DataFrame,
    days: list[dict],
    window_start: date,
    window_end: date,
    run_started_at: datetime,
) -> dict:
    """Señales de calidad por día que se guardan en ``pipeline_run_days.quality``."""
    return business_kpis.quality_by_day(events, heartbeat, days, window_start, window_end, run_started_at)


@task(name="load_kpis", **DB_TASK)
def load_kpis(run_id: str, rows: list[dict], days: list[dict], quality: dict) -> dict:
    """Carga día a día, cada uno en su transacción (§3.1). Un reintento vuelve
    a cargar la ventana entera: los días ya confirmados salen sin cambios."""
    rows_by_day = defaultdict(list)
    for row in rows:
        rows_by_day[row["metric_date"]].append(row)
    totals = Counter(inserted=0, updated=0, unchanged=0, deleted=0)
    with storage.connect(reporting_dsn(), autocommit=True) as connection:
        for day in days:
            try:
                totals.update(storage.load_day(
                    connection, run_id, day, rows_by_day[day["metric_date"]], quality.get(day["metric_date"], {})
                ))
            except psycopg.OperationalError:
                raise
            except psycopg.Error:
                try:
                    storage.record_failed_day(connection, run_id, day)
                except psycopg.Error:
                    get_run_logger().error("Could not record day %s as failed", day["metric_date"])
                raise
    return dict(totals)


@task(name="finish_run", **DB_TASK)
def finish_run(run_id: str, fields: dict) -> None:
    """Cierra la fila de ``pipeline_runs`` con estado y contadores."""
    storage.finish_run(reporting_dsn(), run_id, **fields)


@task(name="export_eval_snapshot", retries=0, cache_policy=NO_CACHE)
def export_eval_snapshot(summary: dict) -> str:
    """Paso no crítico: guarda el resumen de la corrida en
    ``data/eval/business_performance/runs/`` para comparar corridas. Si falla,
    la corrida sigue siendo ``completed``."""
    directory = Path(os.environ.get(config.EVAL_DIR_ENV) or ROOT / "data/eval/business_performance/runs")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{summary['run_id']}.json"
    path.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return str(path)


# --- Flow ------------------------------------------------------------------------


def _close_run_hook(status: str):
    """Hook de Prefect para ``Crashed`` y ``Cancelled``. Solo cierra filas que
    siguen ``running``; si ni siquiera se ejecuta, la siguiente corrida marca
    la fila como ``crashed`` al tomar el candado."""

    def hook(flow, run, state) -> None:
        try:
            storage.finish_run(reporting_dsn(), str(run.id), only_if_running=True, status=status,
                               error_message=(state.message or status)[:500])
        except Exception as exc:  # noqa: BLE001 - un hook no debe fallar
            get_logger("business_performance").warning("Could not close run %s: %s", run.id, type(exc).__name__)

    return hook


def _record_failure(run_id: str, stage: str, exc: BaseException, fields: dict) -> None:
    logger = get_run_logger()
    try:
        # Un solo reintento: la corrida ya ha fallado y no queremos retrasar
        # su estado Failed otros 6 minutos si la base de datos sigue caída.
        finish_run.with_options(retries=1, retry_delay_seconds=10)(run_id, {
            **fields,
            "status": "failed",
            "failed_stage": stage if stage in FAILED_STAGES else None,
            "error_class": type(exc).__name__,
            "error_message": _safe_message(exc),
        })
    except Exception:  # noqa: BLE001
        logger.error("Could not record the failure of run %s; the next run will mark it as crashed", run_id)


@flow(
    name=config.FLOW_NAME,
    version=config.PIPELINE_VERSION,
    on_crashed=[_close_run_hook("crashed")],
    on_cancellation=[_close_run_hook("cancelled")],
)
def business_performance_flow(
    window_start: date | None = None,
    window_end: date | None = None,
    trigger: Literal["schedule", "manual", "backfill"] = "schedule",
    requested_by: str | None = None,
) -> dict:
    """Extract -> transform -> load de los KPIs ejecutivos.

    Sin fechas recalcula los últimos 7 días completos más los días con
    eventos tardíos; con fechas, ``[window_start, window_end)``.
    """
    logger = get_run_logger()
    run_id = str(flow_run.id)
    started_at = datetime.now(timezone.utc)
    today = started_at.date()
    start, end = config.resolve_window(window_start, window_end, today)

    handle = register_run(run_id, trigger, requested_by, start, end)
    if handle.connection is None:
        message = f"Skipped: the pipeline lock is held by run {handle.lock_holder or 'unknown'}"
        logger.warning(message)
        return Cancelled(message=message)

    stage = "extract"
    fields: dict = {}
    try:
        if window_start is None:
            plan = detect_changed_days(today)
            start, end = plan["window_start"], plan["window_end"]
            fields["late_days_detected"] = plan["late_days"]
        fields.update(window_start=start, window_end=end)
        extracted = extract_events(start, end)

        stage = "transform"
        result = transform_kpis(
            extracted["events"], extracted["heartbeat"], extracted["instrumented_since"], start, end
        )
        fields.update(result["totals"])

        # Fallo gestionado de forma explícita: sin las señales de calidad los
        # KPIs siguen siendo correctos, así que la carga continúa y cada día
        # guarda por qué no las tiene.
        quality_state = check_quality(
            extracted["events"], extracted["heartbeat"], result["days"], start, end, started_at, return_state=True
        )
        if quality_state.is_completed():
            quality = quality_state.result()
        else:
            logger.warning("check_quality failed (%s); loading the KPIs without quality signals",
                           quality_state.message)
            quality = {day["metric_date"]: {"unavailable": quality_state.message} for day in result["days"]}

        stage = "load"
        loaded = load_kpis(run_id, result["rows"], result["days"], quality)
        fields.update({f"rows_{name}": count for name, count in loaded.items()})

        stage = "finish"
        finish_run(run_id, {"status": "completed", **fields})
    except Exception as exc:
        _record_failure(run_id, stage, exc, fields)
        raise
    finally:
        handle.connection.close()  # libera el candado

    summary = {
        "run_id": run_id,
        "flow_name": config.FLOW_NAME,
        "trigger": trigger,
        "status": "completed",
        "pipeline_version": config.PIPELINE_VERSION,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        **{key: value.isoformat() if isinstance(value, date) else value for key, value in fields.items()},
        "kpi_status_counts": dict(Counter(row["status"] for row in result["rows"])),
        "quality_available": quality_state.is_completed(),
    }
    # Segundo paso no crítico: un fallo al escribir el snapshot no cambia el
    # resultado de la corrida.
    snapshot = export_eval_snapshot(summary, return_state=True)
    if snapshot.is_completed():
        logger.info("Eval snapshot written to %s", snapshot.result())
    else:
        logger.warning("Eval snapshot not written (%s); the run is still completed", snapshot.message)
    logger.info("pipeline_run %s", json.dumps(summary, default=str))
    return summary


# --- Deployment y línea de comandos ----------------------------------------------------


def serve_deployment() -> None:
    """Deployment diario a las 04:00 UTC con una sola corrida a la vez: si
    coinciden el cron y un disparo manual, la segunda espera en cola
    (``AwaitingConcurrencySlot``) en lugar de correr en paralelo (§6.10)."""
    deployment = business_performance_flow.to_deployment(
        name=config.DEPLOYMENT_NAME,
        schedules=[Cron(config.DEPLOYMENT_CRON, timezone="UTC")],
        concurrency_limit=ConcurrencyLimitConfig(limit=1, collision_strategy=ConcurrencyLimitStrategy.ENQUEUE),
        description="KPIs ejecutivos diarios desde telemetry_events (data/pipelines/PIPELINE_DESIGN.md)",
        version=config.PIPELINE_VERSION,
    )
    serve(deployment)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline de desempeño de negocio de TrackFlow")
    parser.add_argument("--start", type=date.fromisoformat, help="Primer día UTC (incluido), YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, help="Último día UTC (excluido), YYYY-MM-DD")
    parser.add_argument("--serve", action="store_true", help="Registrar el deployment y esperar corridas")
    args = parser.parse_args(argv)
    if args.serve:
        serve_deployment()
        return 0
    state = business_performance_flow(window_start=args.start, window_end=args.end, trigger="manual",
                                      return_state=True)
    if state.is_completed():
        print(json.dumps(state.result(), indent=2))
        return 0
    print(f"Run finished as {state.name}: {state.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
