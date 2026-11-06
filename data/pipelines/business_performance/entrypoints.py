"""Funciones del pipeline que usa ``services/reporting/`` (§5.1 y §5.2).

``services/`` importa de aquí y nunca al revés: las reglas de cálculo, el SQL
y el disparo del flow viven en ``data/``; el router solo valida la petición y
traduce estas excepciones a HTTP.

Lectura con ``REPORTING_READ_DATABASE_DSN`` (rol de login miembro de
``reporting_reader``, solo SELECT en ``reporting.*``). El disparo manual usa
el servidor de Prefect configurado en ``PREFECT_API_URL``; aquí no se ejecuta
el ETL: lo ejecuta el proceso que sirve el deployment.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import httpx
import psycopg
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import (
    DeploymentFilter,
    DeploymentFilterId,
    FlowRunFilter,
    FlowRunFilterState,
    FlowRunFilterStateType,
)
from prefect.client.schemas.objects import StateType
from prefect.deployments import run_deployment
from prefect.exceptions import ObjectNotFound, PrefectException
from prefect.settings import PREFECT_API_URL

from data.pipelines.business_performance import config, storage
from data.process.business_kpis import KPIS, aggregate_weekly, combine_status

DEFAULT_KPI_PERIOD_DAYS = 28
MAX_KPI_PERIOD_DAYS = 366
# Estados en los que una corrida está en marcha o esperando turno. Las
# programadas por el cron para más adelante (Scheduled en el futuro) no cuentan.
WAITING_STATE_NAMES = {"AwaitingConcurrencySlot", "Late", "AwaitingRetry"}


class ReportingUnavailable(Exception):
    """La base de datos de reporting o Prefect no responden."""


class InvalidRequest(ValueError):
    """Parámetros no válidos (422)."""


class RunAlreadyActive(Exception):
    """Ya hay una corrida en marcha o esperando turno (409)."""

    def __init__(self, run_id: str):
        super().__init__(f"Run {run_id} is already active")
        self.run_id = run_id


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _read_dsn() -> str:
    dsn = os.environ.get(config.READ_DSN_ENV)
    if not dsn:
        raise ReportingUnavailable("reporting storage is not configured")
    return dsn


def _with_duration(run: dict | None) -> dict | None:
    if run is not None:
        finished = run["finished_at"]
        run["duration_seconds"] = round((finished - run["started_at"]).total_seconds(), 3) if finished else None
    return run


def get_pipeline_status() -> dict:
    """Última corrida, última completada, corrida activa, frescura de los
    datos y estado de cada KPI y país en el último día calculado."""
    try:
        status = storage.read_status(_read_dsn())
    except psycopg.Error as exc:
        raise ReportingUnavailable("reporting storage read failed") from exc
    last_completed = _with_duration(status["last_completed_run"])
    freshness = None
    if last_completed:
        freshness = round((datetime.now(timezone.utc) - last_completed["finished_at"]).total_seconds() / 3600, 2)
    by_kpi_country: dict[tuple[str, str], list[str]] = {}
    for item in status["statuses"]:
        by_kpi_country.setdefault((item["kpi"], item["country"]), []).append(item["status"])
    return {
        "last_run": _with_duration(status["last_run"]),
        "last_completed_run": last_completed,
        "active_run": _with_duration(status["active_run"]),
        "latest_metric_date": status["latest_metric_date"],
        "latest_computed_at": status["latest_computed_at"],
        "data_freshness_hours": freshness,
        "kpis": [
            {"kpi": kpi, "country": country, "metric_date": status["latest_metric_date"],
             "status": combine_status(statuses)}
            for (kpi, country), statuses in sorted(by_kpi_country.items())
            if kpi in KPIS
        ],
    }


def get_run(run_id: str) -> dict | None:
    """Fila de ``pipeline_runs`` y sus días, o ``None`` si no existe."""
    try:
        return _with_duration(storage.read_run(_read_dsn(), run_id))
    except psycopg.Error as exc:
        raise ReportingUnavailable("reporting storage read failed") from exc


def get_kpis(
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = "day",
    country: str = "all",
) -> dict:
    """Filas de ``executive_kpis_daily`` de ``[start_date, end_date)``: tal
    cual por día, o por semana ISO con ``Σ numerador / Σ denominador``. Por
    defecto, los últimos 28 días completos."""
    end = end_date or _today()
    start = start_date or end - timedelta(days=DEFAULT_KPI_PERIOD_DAYS)
    if start >= end:
        raise InvalidRequest("start_date must be before end_date")
    if (end - start).days > MAX_KPI_PERIOD_DAYS:
        raise InvalidRequest(f"The period cannot exceed {MAX_KPI_PERIOD_DAYS} days")
    if granularity not in ("day", "week"):
        raise InvalidRequest("granularity must be day or week")
    try:
        rows = storage.read_kpi_rows(_read_dsn(), start, end, None if country == "all" else country)
    except psycopg.Error as exc:
        raise ReportingUnavailable("reporting storage read failed") from exc
    if granularity == "week":
        result = aggregate_weekly(rows)
    else:
        result = [
            {**row, "period_start": row["metric_date"], "period_end": row["metric_date"] + timedelta(days=1),
             "days_covered": 1}
            for row in rows
        ]
    return {"start_date": start, "end_date": end, "granularity": granularity, "country": country, "rows": result}


def _active_run_id(client, deployment_id) -> str | None:
    runs = client.read_flow_runs(
        deployment_filter=DeploymentFilter(id=DeploymentFilterId(any_=[deployment_id])),
        flow_run_filter=FlowRunFilter(state=FlowRunFilterState(type=FlowRunFilterStateType(
            any_=[StateType.SCHEDULED, StateType.PENDING, StateType.RUNNING]
        ))),
        limit=50,
    )
    now = datetime.now(timezone.utc)
    for run in runs:
        if run.state_type in (StateType.PENDING, StateType.RUNNING):
            return str(run.id)
        if run.state_name in WAITING_STATE_NAMES or (run.expected_start_time and run.expected_start_time <= now):
            return str(run.id)
    return None


def trigger_run(
    window_start: date | None = None,
    window_end: date | None = None,
    requested_by: str | None = None,
) -> dict:
    """Programa una corrida manual del deployment ``business-performance-daily``
    con ``run_deployment(timeout=0)`` y devuelve su ``run_id`` sin esperar.
    El ``run_id`` es el id del flow run de Prefect, el mismo que tendrá la
    fila de ``reporting.pipeline_runs``."""
    try:
        config.resolve_window(window_start, window_end, _today())
    except config.InvalidWindow as exc:
        raise InvalidRequest(str(exc)) from exc
    if not PREFECT_API_URL.value():
        # Sin servidor configurado, Prefect intentaría arrancar uno temporal
        # dentro de la API.
        raise ReportingUnavailable("Prefect API is not configured (PREFECT_API_URL)")
    parameters = {
        "window_start": window_start.isoformat() if window_start else None,
        "window_end": window_end.isoformat() if window_end else None,
        "trigger": "manual",
        "requested_by": requested_by,
    }
    try:
        with get_client(sync_client=True) as client:
            deployment = client.read_deployment_by_name(config.DEPLOYMENT_PATH)
            active = _active_run_id(client, deployment.id)
        if active:
            raise RunAlreadyActive(active)
        flow_run = run_deployment(name=deployment.id, parameters=parameters, timeout=0, as_subflow=False,
                                  tags=["manual"])
    except ObjectNotFound as exc:
        raise ReportingUnavailable("Deployment business-performance-daily is not registered") from exc
    except (httpx.HTTPError, PrefectException, OSError) as exc:
        raise ReportingUnavailable("Prefect API unavailable") from exc
    return {"run_id": str(flow_run.id), "status": "scheduled"}
