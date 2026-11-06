"""Bulk writer for ``public.telemetry_events`` (Supabase Postgres).

The DSN is read from ``TELEMETRY_DATABASE_DSN`` and only lives in the backend.
It should use a login role granted ``telemetry_writer``, which can INSERT and
nothing else (see ``supabase/migrations``). Errors never include the DSN.
"""
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

import psycopg

from app.schemas.telemetry import DEFS, SCHEMA_VERSION, TELEMETRY_EVENT_ADAPTER

logger = logging.getLogger("trackflow.telemetry")
UUID_PATTERN = re.compile(DEFS["uuid"]["pattern"])

# One statement for the whole batch: either every new row is inserted or none.
# Already stored eventIds are skipped, so client retries are idempotent. The
# conflict target is left out on purpose: naming (event_id) would require
# SELECT on that column, and the primary key is the table's only unique key.
INSERT_EVENTS = """
insert into public.telemetry_events
  (event_id, event_type, "timestamp", service, session_id, user_id, request_id, tags)
select event_id, event_type, "timestamp", service, session_id, user_id, request_id, tags
from jsonb_to_recordset(%s::jsonb) as e(
  event_id uuid, event_type text, "timestamp" timestamptz, service text,
  session_id uuid, user_id text, request_id uuid, tags jsonb
)
on conflict do nothing
"""


class TelemetryStoreError(Exception):
    """The batch could not be written; nothing from it was stored."""


def to_row(event) -> dict:
    """Map a validated event to a table row. ``service`` is the frontend app
    when the event carries one, otherwise the catalog source (``x-source``)."""
    data = event.model_dump(mode="json", exclude_unset=True)
    properties = data["properties"]
    return {
        "event_id": data["eventId"],
        "event_type": data["event_type"],
        "timestamp": data["timestamp"],
        "service": properties.get("app") or DEFS["events"][data["event_type"]]["x-source"],
        "session_id": data["sessionId"],
        "user_id": data["userId"],
        "request_id": data["requestId"],
        "tags": {**properties, "schemaVersion": data["schemaVersion"]},
    }


def store_events(rows: list[dict]) -> int:
    """Insert ``rows`` in a single statement and return how many were new."""
    if not rows:
        return 0
    dsn = os.environ.get("TELEMETRY_DATABASE_DSN")
    if not dsn:
        raise TelemetryStoreError("telemetry storage is not configured")
    try:
        with psycopg.connect(dsn, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute(INSERT_EVENTS, (json.dumps(rows),))
                return cursor.rowcount
    except psycopg.Error as exc:
        raise TelemetryStoreError("telemetry storage write failed") from exc


def request_id_from(header: str | None) -> str:
    """Reuse a contract-valid ``X-Request-Id`` or create one for this request."""
    if header and UUID_PATTERN.match(header.strip().lower()):
        return header.strip().lower()
    return str(uuid.uuid4())


def emit_event(event_type: str, properties: dict, *, occurred_at: datetime | None, request_id: str) -> None:
    """Validate and store one backend event. It runs after the response and
    never raises: a telemetry failure must not affect the operation itself."""
    try:
        moment = (occurred_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        event = TELEMETRY_EVENT_ADAPTER.validate_python({
            "eventId": str(uuid.uuid4()),
            "timestamp": moment.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "sessionId": None,
            "userId": None,
            "event_type": event_type,
            "schemaVersion": SCHEMA_VERSION,
            "requestId": request_id,
            "properties": properties,
        })
        store_events([to_row(event)])
    except Exception as exc:  # noqa: BLE001 - any failure is logged and dropped
        logger.warning("telemetry_emit_failed event_type=%s error=%s", event_type, type(exc).__name__)
