import logging

from fastapi import APIRouter

from app.schemas.telemetry import TelemetryAck, TelemetryBatch

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
logger = logging.getLogger("trackflow.telemetry")


@router.post("/events", response_model=TelemetryAck)
def ingest_events(batch: TelemetryBatch) -> TelemetryAck:
    """Accept a contract-valid batch. There is no event store yet: accepted
    events are only written to the log, and invalid batches never reach here."""
    for event in batch.events:
        logger.info("telemetry_event %s", event.model_dump_json(exclude_unset=True))
    return TelemetryAck(received=len(batch.events))
