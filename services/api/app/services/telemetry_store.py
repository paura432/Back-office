"""Bulk writer for ``public.telemetry_events`` (Supabase Postgres).

The DSN is read from ``TELEMETRY_DATABASE_DSN`` and only lives in the backend.
It should use a login role granted ``telemetry_writer``, which can INSERT and
nothing else (see ``supabase/migrations``). Errors never include the DSN.
"""
import json
import os

import psycopg

from app.schemas.telemetry import DEFS

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
