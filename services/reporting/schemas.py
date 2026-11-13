"""Contratos de respuesta de /reporting (PIPELINE_DESIGN.md §5.2)."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

KpiName = Literal[
    "shipments_total",
    "on_time_delivery_rate",
    "shipping_cost_total",
    "shipping_cost_per_kg",
    "return_rate",
    "customer_satisfaction_avg",
]
KpiStatusName = Literal["ok", "no_activity", "capture_gap", "not_instrumented"]
RunStatusName = Literal["running", "completed", "failed", "crashed", "cancelled", "skipped"]


class PipelineRun(BaseModel):
    """Fila de ``reporting.pipeline_runs``. ``events_extracted`` son los
    registros procesados; ``error_message`` nunca lleva DSN ni credenciales."""

    model_config = ConfigDict(extra="ignore")

    run_id: UUID
    flow_name: str
    trigger: Literal["schedule", "manual", "backfill"]
    requested_by: str | None
    window_start: date
    window_end: date
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None
    status: RunStatusName
    failed_stage: Literal["extract", "transform", "quality", "load"] | None
    last_completed_date: date | None
    events_extracted: int
    events_deduplicated: int
    events_invalid: int
    rows_inserted: int
    rows_updated: int
    rows_unchanged: int
    rows_deleted: int
    late_days_detected: int
    source_max_timestamp: datetime | None
    pipeline_version: str
    error_class: str | None
    error_message: str | None


class PipelineRunDay(BaseModel):
    metric_date: date
    status: Literal["loaded", "failed"]
    events_extracted: int
    events_after_dedupe: int
    rows_written: int
    source_checksum: str
    quality: dict
    finished_at: datetime


class PipelineRunDetail(PipelineRun):
    days: list[PipelineRunDay]


class KpiDayStatus(BaseModel):
    kpi: KpiName
    country: str
    metric_date: date
    status: KpiStatusName


class PipelineStatus(BaseModel):
    last_run: PipelineRun | None
    last_completed_run: PipelineRun | None
    active_run: PipelineRun | None = Field(description="Run still marked as running, if any.")
    latest_metric_date: date | None
    latest_computed_at: datetime | None
    data_freshness_hours: float | None = Field(description="Hours since the last completed run finished.")
    kpis: list[KpiDayStatus] = Field(description="Status of each KPI and country on latest_metric_date.")


class RunRequest(BaseModel):
    """Sin fechas, la ventana automática: últimos 7 días completos más los
    días con eventos tardíos. Con fechas, ``[window_start, window_end)``."""

    model_config = ConfigDict(extra="forbid")

    window_start: date | None = None
    window_end: date | None = None
    requested_by: str | None = Field(None, pattern=r"^usr_[0-9a-f]{32}$")


class RunAccepted(BaseModel):
    run_id: UUID
    status: Literal["scheduled"]


class RunConflict(BaseModel):
    detail: str
    run_id: UUID


class KpiRow(BaseModel):
    kpi: KpiName
    period_start: date
    period_end: date = Field(description="Exclusive.")
    country: str
    carrier: str = Field(description="Carrier code, n/a, or all in weekly rows.")
    currency: Literal["USD", "EUR", "n/a"]
    numerator: float
    denominator: float | None
    value: float | None = Field(description="numerator / denominator, or numerator; null when it cannot be measured.")
    unit: str
    status: KpiStatusName
    days_covered: int
    revision: int
    computed_at: datetime


class KpiResponse(BaseModel):
    start_date: date
    end_date: date = Field(description="Exclusive.")
    granularity: Literal["day", "week"]
    country: str
    rows: list[KpiRow]
