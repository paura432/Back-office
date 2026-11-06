"""Tests del reporte técnico contra PostgreSQL real (Supabase local).

Solo se ejecutan si existen ``TELEMETRY_TEST_DATABASE_DSN`` (login con
``telemetry_writer``), ``TELEMETRY_TEST_READER_DSN`` (login con
``telemetry_reader``) y ``TELEMETRY_TEST_ADMIN_DSN`` (propietario), sobre una
base de test con las migraciones de ``supabase/migrations`` aplicadas. Las
filas no se pueden borrar, así que cada test escribe en un periodo propio del
año 2099 que ningún otro test usa.
"""
import os
import random
import uuid
from datetime import datetime, time, timedelta, timezone

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from psycopg.conninfo import make_conninfo

from app.routers import telemetry as telemetry_router
from app.services.telemetry_store import store_events
from app.services.ttl_cache import TTLCache
from app.telemetry import analysis
from main import app

WRITER_DSN = os.environ.get("TELEMETRY_TEST_DATABASE_DSN")
READER_DSN = os.environ.get("TELEMETRY_TEST_READER_DSN")
ADMIN_DSN = os.environ.get("TELEMETRY_TEST_ADMIN_DSN")

pytestmark = pytest.mark.skipif(
    not (WRITER_DSN and READER_DSN and ADMIN_DSN), reason="sin base de test de telemetría (TELEMETRY_TEST_*_DSN)"
)


@pytest.fixture
def period(monkeypatch):
    """Un día del año 2099 que no se repite entre ejecuciones (al minuto)."""
    monkeypatch.setenv("TELEMETRY_DATABASE_DSN", WRITER_DSN)
    monkeypatch.setenv("TELEMETRY_READ_DATABASE_DSN", READER_DSN)
    start = datetime(2099, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=random.randrange(500_000))
    return start, start + timedelta(days=1)


def write(moment, event_type="page_viewed", session_id=None, **tags):
    tags = tags or {"app": "backoffice", "route_template": "/", "viewport_class": "desktop"}
    store_events([{
        "event_id": str(uuid.uuid4()), "event_type": event_type, "timestamp": moment.isoformat(),
        "service": "backoffice", "session_id": session_id or str(uuid.uuid4()), "user_id": None,
        "request_id": None, "tags": {**tags, "schemaVersion": "1.0.0"},
    }])


def page_views(rows):
    return {row["date"]: row["events"] for row in rows if row["event_type"] == "page_viewed"}


def test_period_start_is_inclusive_and_end_is_exclusive(period):
    start, end = period
    ms = timedelta(milliseconds=1)
    for moment in (start - ms, start, start + timedelta(hours=1), end - ms, end):
        write(moment)
    assert sum(page_views(analysis.events_per_day(start, end)).values()) == 3


def test_tags_from_jsonb_feed_every_metric(period):
    start, _ = period
    session = str(uuid.uuid4())
    write(start, session_id=session)
    write(start, "web_vitals_measured", session, app="backoffice", route_template="/", metric="LCP", value=1200.5,
          rating="needs_improvement")
    write(start, "frontend_error_occurred", session, app="backoffice", route_template="/", error_kind="fetch_failed",
          error_fingerprint="0123456789abcdef", http_status=503)
    report = analysis.build_report(*period)["metrics"]
    day = start.date().isoformat()
    assert report["error_rate_per_day"] == [
        {"date": day, "app": "backoffice", "sessions": 1, "sessions_with_errors": 1, "errors": 1, "error_rate": 1.0},
    ]
    assert report["frontend_errors_per_day"] == [
        {"date": day, "app": "backoffice", "route_template": "/", "error_kind": "fetch_failed",
         "errors": 1, "distinct_errors": 1, "sessions": 1},
    ]
    assert report["web_vitals_per_day"] == [
        {"date": day, "app": "backoffice", "route_template": "/", "metric": "LCP", "unit": "ms",
         "samples": 1, "mean": 1200.5, "p75": 1200.5, "poor_rate": 0.0},
    ]


def test_dates_are_utc_even_if_the_session_time_zone_is_not(period, monkeypatch):
    """Con la sesión en Los Ángeles, psycopg devuelve las 03:00 UTC como las
    19:00 del día anterior. Sin pasar a UTC el evento caería en otro día."""
    start, end = period
    late = datetime.combine(start.date() + timedelta(days=1), time(3), tzinfo=timezone.utc)
    if late >= end:
        late -= timedelta(days=1)
    write(late)
    monkeypatch.setenv("TELEMETRY_READ_DATABASE_DSN", make_conninfo(READER_DSN, options="-c TimeZone=America/Los_Angeles"))
    assert page_views(analysis.events_per_day(start, end)) == {late.date().isoformat(): 1}


async def test_report_endpoint_over_real_storage(period, monkeypatch):
    start, end = period
    write(start + timedelta(minutes=1))
    monkeypatch.setattr(telemetry_router, "report_cache", TTLCache(60))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/telemetry/report", params={"start_date": start.isoformat(), "end_date": end.isoformat()})
    assert resp.status_code == 200
    assert page_views(resp.json()["metrics"]["events_per_day"]) == {start.date().isoformat(): 1}


@pytest.mark.parametrize("statement", [
    "insert into public.telemetry_events (event_id, event_type, \"timestamp\", service, tags)"
    " values (gen_random_uuid(), 'page_viewed', now(), 'backoffice', '{}')",
    "update public.telemetry_events set service = 'x'",
    "delete from public.telemetry_events",
    "truncate public.telemetry_events",
])
def test_reader_role_can_only_select(statement):
    with psycopg.connect(READER_DSN) as connection:
        assert connection.execute("select count(*) from public.telemetry_events").fetchone()[0] >= 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
            connection.execute(statement)


def test_reader_policy_is_select_only():
    with psycopg.connect(ADMIN_DSN) as connection:
        policies = connection.execute(
            "select polname, polcmd, polroles::regrole[]::text from pg_policy"
            " where polrelid = 'public.telemetry_events'::regclass order by polname"
        ).fetchall()
    assert policies == [
        ("telemetry_reader_select", "r", "{telemetry_reader}"),
        ("telemetry_writer_insert", "a", "{telemetry_writer}"),
    ]
