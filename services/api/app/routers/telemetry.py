import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from app.schemas.telemetry import TELEMETRY_EVENT_ADAPTER, TelemetryAck, TelemetryBatch, TelemetryReport
from app.services.telemetry_store import TelemetryStoreError, store_events, to_row
from app.services.ttl_cache import TTLCache
from app.telemetry.analysis import TelemetryReportError, build_report

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
logger = logging.getLogger("trackflow.telemetry")

DEFAULT_REPORT_PERIOD = timedelta(days=7)
MAX_REPORT_PERIOD = timedelta(days=90)
REPORT_TTL_SECONDS = 60
report_cache: TTLCache[dict] = TTLCache(REPORT_TTL_SECONDS)


@router.post(
    "/events",
    response_model=TelemetryAck,
    responses={503: {"description": "Telemetry storage unavailable; no event of the batch was stored."}},
)
def ingest_events(batch: TelemetryBatch) -> TelemetryAck:
    """Validate each event on its own, reject the invalid ones and store the
    valid ones in a single bulk insert. If the write fails nothing is stored
    and the client gets a 503 so it can retry with the same eventIds."""
    valid, seen, rejected = [], set(), 0
    for raw in batch.events:
        try:
            event = TELEMETRY_EVENT_ADAPTER.validate_python(raw)
        except ValidationError:
            rejected += 1
            continue
        if event.eventId not in seen:
            seen.add(event.eventId)
            valid.append(event)
    try:
        stored = store_events([to_row(event) for event in valid])
    except TelemetryStoreError as exc:
        logger.error("telemetry_store_failed events=%d reason=%s", len(valid), exc)
        raise HTTPException(status_code=503, detail="Telemetry storage unavailable") from exc
    ack = TelemetryAck(received=len(batch.events), stored=stored, rejected=rejected)
    logger.info(
        "telemetry_batch received=%d stored=%d rejected=%d duplicates=%d",
        ack.received, ack.stored, ack.rejected, ack.received - ack.stored - ack.rejected,
    )
    return ack


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _utc(moment: datetime | None) -> datetime | None:
    """Naive datetimes are read as UTC; aware ones are converted to UTC."""
    if moment is None:
        return None
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


@router.get(
    "/report",
    response_model=TelemetryReport,
    responses={
        422: {"description": "Invalid period: start_date must be before end_date and span at most 90 days."},
        503: {"description": "Telemetry storage unavailable; no report was produced."},
    },
)
def telemetry_report(
    start_date: datetime | None = Query(None, description="ISO 8601, inclusive. Default: end_date - 7 days."),
    end_date: datetime | None = Query(None, description="ISO 8601, exclusive. Default: now (UTC)."),
) -> dict:
    """Technical report over ``[start_date, end_date)``. The period is resolved
    here once and passed to every metric. The result is cached for 60 s per
    ``start_date``/``end_date`` combination as requested (omitted values
    included), so repeated requests in that window do not run the pipeline."""
    start_param, end_param = _utc(start_date), _utc(end_date)
    end = end_param or _now()
    start = start_param or end - DEFAULT_REPORT_PERIOD
    if start >= end:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")
    if end - start > MAX_REPORT_PERIOD:
        raise HTTPException(status_code=422, detail="The period cannot exceed 90 days")
    try:
        return report_cache.get_or_set((start_param, end_param), lambda: build_report(start, end))
    except TelemetryReportError as exc:
        logger.error("telemetry_report_failed reason=%s", exc)
        raise HTTPException(status_code=503, detail="Telemetry report unavailable") from exc
