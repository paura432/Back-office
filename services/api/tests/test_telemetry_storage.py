"""Tests de almacenamiento de telemetría contra PostgreSQL real (Supabase local).

Solo se ejecutan si existen ``TELEMETRY_TEST_DATABASE_DSN`` (login con el rol
``telemetry_writer``) y ``TELEMETRY_TEST_ADMIN_DSN`` (propietario, para
comprobar), ambos sobre una base de desarrollo/test con la migración de
``supabase/migrations`` aplicada. Las filas no se pueden borrar: cada test usa
eventId nuevos.
"""
import os
import uuid

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient

from app.services.telemetry_store import TelemetryStoreError, store_events
from main import app

WRITER_DSN = os.environ.get("TELEMETRY_TEST_DATABASE_DSN")
ADMIN_DSN = os.environ.get("TELEMETRY_TEST_ADMIN_DSN")

pytestmark = pytest.mark.skipif(
    not (WRITER_DSN and ADMIN_DSN), reason="sin base de test de telemetría (TELEMETRY_TEST_*_DSN)"
)


def page_viewed(event_id=None):
    return {
        "eventId": event_id or str(uuid.uuid4()),
        "timestamp": "2026-10-26T09:15:02.120Z",
        "sessionId": str(uuid.uuid4()),
        "userId": None,
        "event_type": "page_viewed",
        "schemaVersion": "1.0.0",
        "requestId": None,
        "properties": {"app": "backoffice", "route_template": "/", "viewport_class": "desktop"},
    }


def movement():
    return {
        **page_viewed(),
        "event_type": "inventory_movement_recorded",
        "sessionId": None,
        "requestId": str(uuid.uuid4()),
        "properties": {"sku": "DEMO-BOX-001", "warehouse": "zaragoza", "quantity_delta": -3, "quantity_after": 5},
    }


def admin_query(sql, params=None):
    with psycopg.connect(ADMIN_DSN) as connection:
        return connection.execute(sql, params).fetchall()


def stored(ids):
    rows = admin_query(
        'select event_id::text, event_type, "timestamp", service, session_id::text, user_id, request_id::text, tags'
        " from public.telemetry_events where event_id = any(%s::uuid[]) order by event_type",
        (list(ids),),
    )
    return {row[0]: row for row in rows}


@pytest.fixture
async def post(monkeypatch):
    monkeypatch.setenv("TELEMETRY_DATABASE_DSN", WRITER_DSN)

    async def send(events):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/telemetry/events", json={"events": events})

    return send


async def test_mixed_batch_is_persisted_with_every_column(post):
    page, move = page_viewed(), movement()
    invalid = {**page_viewed(), "properties": {"app": "backoffice"}}
    resp = await post([page, move, invalid])
    assert resp.status_code == 200
    assert resp.json() == {"received": 3, "stored": 2, "rejected": 1}

    rows = stored([page["eventId"], move["eventId"], invalid["eventId"]])
    assert set(rows) == {page["eventId"], move["eventId"]}
    _, event_type, timestamp, service, session_id, user_id, request_id, tags = rows[move["eventId"]]
    assert (event_type, service, session_id, user_id, request_id) == (
        "inventory_movement_recorded", "backend", None, None, move["requestId"])
    assert timestamp.isoformat() == "2026-10-26T09:15:02.120000+00:00"
    assert tags == {**move["properties"], "schemaVersion": "1.0.0"}
    assert rows[page["eventId"]][3] == "backoffice"
    assert rows[page["eventId"]][4] == page["sessionId"]


async def test_resent_batch_is_idempotent(post):
    batch = [page_viewed(), page_viewed()]
    first, second = await post(batch), await post(batch)
    assert first.json() == {"received": 2, "stored": 2, "rejected": 0}
    assert second.json() == {"received": 2, "stored": 0, "rejected": 0}
    assert len(stored(e["eventId"] for e in batch)) == 2


async def test_storage_failure_returns_503_and_stores_nothing(post, monkeypatch):
    monkeypatch.setenv("TELEMETRY_DATABASE_DSN", WRITER_DSN.replace("://trackflow_api_local:", "://trackflow_api_local:wrong"))
    batch = [page_viewed()]
    resp = await post(batch)
    assert resp.status_code == 503
    assert "stored" not in resp.json()
    assert stored([batch[0]["eventId"]]) == {}


def test_bulk_insert_is_all_or_nothing(monkeypatch):
    monkeypatch.setenv("TELEMETRY_DATABASE_DSN", WRITER_DSN)
    good = {"event_id": str(uuid.uuid4()), "event_type": "page_viewed", "timestamp": "2026-10-26T09:15:02Z",
            "service": "backoffice", "session_id": None, "user_id": None, "request_id": None, "tags": {}}
    breaks_check = {**good, "event_id": str(uuid.uuid4()), "service": ""}
    with pytest.raises(TelemetryStoreError):
        store_events([good, breaks_check])
    assert stored([good["event_id"], breaks_check["event_id"]]) == {}


@pytest.mark.parametrize("statement", [
    "update public.telemetry_events set service = 'x' where event_id = %s",
    "delete from public.telemetry_events where event_id = %s",
])
def test_events_are_immutable_even_for_the_owner(monkeypatch, statement):
    monkeypatch.setenv("TELEMETRY_DATABASE_DSN", WRITER_DSN)
    row = {"event_id": str(uuid.uuid4()), "event_type": "page_viewed", "timestamp": "2026-10-26T09:15:02Z",
           "service": "backoffice", "session_id": None, "user_id": None, "request_id": None, "tags": {}}
    assert store_events([row]) == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="append-only"):
        admin_query(statement, (row["event_id"],))
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="append-only"):
        admin_query("truncate public.telemetry_events")
    assert stored([row["event_id"]])[row["event_id"]][3] == "backoffice"


@pytest.mark.parametrize("statement", [
    "select count(*) from public.telemetry_events",
    "update public.telemetry_events set service = 'x'",
    "delete from public.telemetry_events",
])
def test_backend_role_can_only_insert(statement):
    with psycopg.connect(WRITER_DSN) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
            connection.execute(statement)


@pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
@pytest.mark.parametrize("statement", [
    "select count(*) from public.telemetry_events",
    "insert into public.telemetry_events (event_id, event_type, \"timestamp\", service, tags)"
    " values (gen_random_uuid(), 'page_viewed', now(), 'backoffice', '{}')",
])
def test_data_api_roles_have_no_access(role, statement):
    with psycopg.connect(ADMIN_DSN) as connection:
        connection.execute(f"set role {role}")
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
            connection.execute(statement)


def test_event_id_is_the_only_unique_key():
    """``on conflict do nothing`` has no target: another unique key would make
    it skip rows that are not duplicates of an eventId."""
    assert admin_query(
        "select a.attname from pg_index i join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)"
        " where i.indrelid = 'public.telemetry_events'::regclass and i.indisunique"
    ) == [("event_id",)]


def test_row_level_security_is_enabled_and_forced():
    assert admin_query(
        "select relrowsecurity, relforcerowsecurity from pg_class where oid = 'public.telemetry_events'::regclass"
    ) == [(True, True)]


@pytest.mark.parametrize("index, query", [
    ("telemetry_events_timestamp_idx",
     "select event_id from public.telemetry_events where \"timestamp\" >= now() - interval '1 day'"),
    ("telemetry_events_event_type_idx",
     "select event_id from public.telemetry_events where event_type = 'page_viewed'"),
    ("telemetry_events_tags_idx",
     "select event_id from public.telemetry_events where tags @> '{\"warehouse\": \"zaragoza\"}'"),
])
def test_indexes_are_used_by_their_queries(index, query):
    with psycopg.connect(ADMIN_DSN) as connection:
        connection.execute("set enable_seqscan = off")
        plan = "\n".join(row[0] for row in connection.execute(f"explain {query}"))
    assert index in plan
