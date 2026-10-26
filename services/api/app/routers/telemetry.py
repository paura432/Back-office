import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.schemas.telemetry import TELEMETRY_EVENT_ADAPTER, TelemetryAck, TelemetryBatch
from app.services.telemetry_store import TelemetryStoreError, store_events, to_row

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
logger = logging.getLogger("trackflow.telemetry")


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
