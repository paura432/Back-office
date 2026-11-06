"""Endpoints del pipeline de desempeño de negocio (PIPELINE_DESIGN.md §5.2).

Separados de ``/telemetry``: aquí solo se valida la petición y se traducen los
errores a HTTP. El SQL, las reglas de cálculo y el disparo del flow están en
``data/pipelines/business_performance/entrypoints.py``.
"""
import logging
import os
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from data.pipelines.business_performance import entrypoints

from .schemas import KpiResponse, PipelineRunDetail, PipelineStatus, RunAccepted, RunConflict, RunRequest

router = APIRouter(prefix="/reporting", tags=["reporting"])
logger = logging.getLogger("trackflow.reporting")

UNAVAILABLE = {503: {"description": "Reporting storage or Prefect unavailable."}}
MANUAL_RUN_ENVIRONMENTS = {"development", "test"}


def _unavailable(exc: entrypoints.ReportingUnavailable) -> HTTPException:
    logger.error("reporting_unavailable reason=%s", exc)
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reporting unavailable")


@router.get("/pipeline/status", response_model=PipelineStatus, responses=UNAVAILABLE)
def pipeline_status() -> dict:
    """Last run and last completed run (status, window, start and end time,
    events processed, sanitized error), active run, data freshness and the
    status of each KPI on the latest computed day."""
    try:
        return entrypoints.get_pipeline_status()
    except entrypoints.ReportingUnavailable as exc:
        raise _unavailable(exc) from exc


@router.post(
    "/pipeline/runs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RunAccepted,
    responses={
        404: {"description": "Manual runs are only enabled in development and test."},
        409: {"model": RunConflict, "description": "A run is already running or waiting for its slot."},
        422: {"description": "Invalid window (both dates or none, start before end, at most 90 days)."},
        **UNAVAILABLE,
    },
)
def trigger_pipeline_run(body: RunRequest | None = None):
    """Schedule a manual run of the business-performance-daily deployment
    and return its run_id without waiting for it. There is no
    authentication yet (auth routes are 501 stubs), so, like the inventory
    demo, it is only enabled with APP_ENV development or test."""
    if os.getenv("APP_ENV", "").strip().lower() not in MANUAL_RUN_ENVIRONMENTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual pipeline runs are not enabled")
    body = body or RunRequest()
    try:
        return entrypoints.trigger_run(body.window_start, body.window_end, body.requested_by)
    except entrypoints.InvalidRequest as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except entrypoints.RunAlreadyActive as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "A pipeline run is already active", "run_id": exc.run_id},
        )
    except entrypoints.ReportingUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get(
    "/pipeline/runs/{run_id}",
    response_model=PipelineRunDetail,
    responses={404: {"description": "Unknown run_id."}, **UNAVAILABLE},
)
def pipeline_run(run_id: UUID) -> dict:
    """One run of reporting.pipeline_runs with its per-day checkpoint."""
    try:
        run = entrypoints.get_run(str(run_id))
    except entrypoints.ReportingUnavailable as exc:
        raise _unavailable(exc) from exc
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")
    return run


@router.get(
    "/kpis",
    response_model=KpiResponse,
    responses={422: {"description": "Invalid period: start before end, at most 366 days."}, **UNAVAILABLE},
)
def kpis(
    start_date: date | None = Query(None, description="First UTC day, inclusive. Default: end_date - 28 days."),
    end_date: date | None = Query(None, description="Last UTC day, exclusive. Default: today (UTC)."),
    granularity: str = Query("day", pattern="^(day|week)$"),
    country: str = Query("all", pattern="^([A-Z]{2}|unknown|all)$"),
) -> dict:
    """KPI rows of the destination table: per day as stored, or per ISO week
    as sum(numerator) / sum(denominator). Feed of the Part 3 dashboard."""
    try:
        return entrypoints.get_kpis(start_date, end_date, granularity, country)
    except entrypoints.InvalidRequest as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except entrypoints.ReportingUnavailable as exc:
        raise _unavailable(exc) from exc
