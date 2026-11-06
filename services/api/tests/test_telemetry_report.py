"""Tests del pipeline de análisis (app/telemetry/analysis.py) y de GET /telemetry/report.

La carga SQL se sustituye por un cargador falso que aplica la misma ventana
[start, end) y el mismo filtro de event_type que la consulta real, y devuelve
los timestamps como texto, igual que llegarían de una API REST. La consulta
real se prueba en test_telemetry_report_storage.py.
"""
import ast
import inspect
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from app.routers import telemetry as telemetry_router
from app.services.ttl_cache import TTLCache
from app.telemetry import analysis
from main import app

START = datetime(2026, 11, 5, tzinfo=timezone.utc)
END = datetime(2026, 11, 7, tzinfo=timezone.utc)
S1, S2, S3, S4 = (f"00000000-0000-4000-8000-00000000000{n}" for n in range(1, 5))
PAGE = {"app": "backoffice", "route_template": "/", "viewport_class": "desktop"}


def vital(metric, value, rating, route="/"):
    return {"app": "backoffice", "route_template": route, "metric": metric, "value": value, "rating": rating}


def failure(kind, fingerprint, route="/"):
    return {"app": "backoffice", "route_template": route, "error_kind": kind, "error_fingerprint": fingerprint}


def row(timestamp, event_type, session_id, tags, service="backoffice"):
    return {"timestamp": timestamp, "event_type": event_type, "service": service, "session_id": session_id, "tags": tags}


ROWS = [
    row("2026-11-04T23:59:59.999Z", "page_viewed", S1, PAGE),  # antes del periodo
    row("2026-11-05T08:00:00Z", "page_viewed", S1, PAGE),
    row("2026-11-05T08:00:01Z", "web_vitals_measured", S1, vital("TTFB", 100, "good")),
    row("2026-11-05T08:00:02Z", "web_vitals_measured", S1, vital("TTFB", 300, "needs_improvement")),
    row("2026-11-05T08:00:03Z", "web_vitals_measured", S1, vital("CLS", 0.05, "good")),
    row("2026-11-05T08:05:00Z", "frontend_error_occurred", S1, {**failure("fetch_failed", "a" * 16), "http_status": 503}),
    row("2026-11-05T08:06:00Z", "frontend_error_occurred", S1, failure("fetch_failed", "b" * 16)),
    row("2026-11-05T09:00:00Z", "page_viewed", S2, PAGE),
    row("2026-11-05T09:00:01Z", "web_vitals_measured", S2, vital("TTFB", 900, "poor")),
    # 00:30 en +01:00 es el 5 de noviembre en UTC: agrupar el texto lo pondría el día 6.
    row("2026-11-06T00:30:00+01:00", "page_viewed", S3, PAGE),
    row("2026-11-06T10:00:00Z", "page_viewed", S4, {**PAGE, "route_template": "/telemetry"}),
    row("2026-11-06T10:00:05Z", "frontend_error_occurred", S4, failure("js_exception", "c" * 16, "/telemetry")),
    row("2026-11-06T11:00:00Z", "inventory_movement_recorded", None,
        {"sku": "DEMO-BOX-001", "warehouse": "zaragoza", "quantity_delta": -1, "quantity_after": 4}, service="backend"),
    row("2026-11-07T00:00:00Z", "page_viewed", S4, PAGE),  # fin exclusivo
]


class FakeLoader:
    """Emula load_events: misma ventana y filtro que el SQL, solo las columnas
    pedidas y timestamps como texto. Registra cada llamada."""

    def __init__(self, rows=ROWS, as_datetime=None):
        self.rows, self.as_datetime, self.calls = rows, as_datetime, []

    def __call__(self, columns, start, end, event_types=None):
        self.calls.append((tuple(columns), start, end, event_types))
        selected = [
            {**r, "timestamp": self.as_datetime(r["timestamp"]) if self.as_datetime else r["timestamp"]}
            for r in self.rows
            if start <= datetime.fromisoformat(r["timestamp"]) < end
            and (event_types is None or r["event_type"] in event_types)
        ]
        return pd.DataFrame(selected, columns=list(columns))


@pytest.fixture
def loader(monkeypatch):
    fake = FakeLoader()
    monkeypatch.setattr(analysis, "load_events", fake)
    return fake


def test_each_metric_loads_only_its_columns_and_event_types_for_the_given_period(loader):
    analysis.build_report(START, END)
    assert loader.calls == [
        (("timestamp", "service", "event_type"), START, END, None),
        (("timestamp", "event_type", "session_id", "tags"), START, END, ("page_viewed", "frontend_error_occurred")),
        (("timestamp", "session_id", "tags"), START, END, ("frontend_error_occurred",)),
        (("timestamp", "tags"), START, END, ("web_vitals_measured",)),
    ]


def test_events_per_day_groups_by_utc_date_and_shows_each_type_share(loader):
    assert analysis.events_per_day(START, END) == [
        {"date": "2026-11-05", "service": "backoffice", "event_type": "frontend_error_occurred", "events": 2, "share": 0.2222},
        {"date": "2026-11-05", "service": "backoffice", "event_type": "page_viewed", "events": 3, "share": 0.3333},
        {"date": "2026-11-05", "service": "backoffice", "event_type": "web_vitals_measured", "events": 4, "share": 0.4444},
        {"date": "2026-11-06", "service": "backend", "event_type": "inventory_movement_recorded", "events": 1, "share": 0.3333},
        {"date": "2026-11-06", "service": "backoffice", "event_type": "frontend_error_occurred", "events": 1, "share": 0.3333},
        {"date": "2026-11-06", "service": "backoffice", "event_type": "page_viewed", "events": 1, "share": 0.3333},
    ]


def test_error_rate_per_day_is_the_share_of_sessions_with_errors(loader):
    assert analysis.error_rate_per_day(START, END) == [
        {"date": "2026-11-05", "app": "backoffice", "sessions": 3, "sessions_with_errors": 1, "errors": 2, "error_rate": 0.3333},
        {"date": "2026-11-06", "app": "backoffice", "sessions": 1, "sessions_with_errors": 1, "errors": 1, "error_rate": 1.0},
    ]


def test_frontend_errors_per_day_by_route_and_kind(loader):
    assert analysis.frontend_errors_per_day(START, END) == [
        {"date": "2026-11-05", "app": "backoffice", "route_template": "/", "error_kind": "fetch_failed",
         "errors": 2, "distinct_errors": 2, "sessions": 1},
        {"date": "2026-11-06", "app": "backoffice", "route_template": "/telemetry", "error_kind": "js_exception",
         "errors": 1, "distinct_errors": 1, "sessions": 1},
    ]


def test_web_vitals_per_day_mean_p75_and_poor_rate(loader):
    assert analysis.web_vitals_per_day(START, END) == [
        {"date": "2026-11-05", "app": "backoffice", "route_template": "/", "metric": "CLS", "unit": "score",
         "samples": 1, "mean": 0.05, "p75": 0.05, "poor_rate": 0.0},
        {"date": "2026-11-05", "app": "backoffice", "route_template": "/", "metric": "TTFB", "unit": "ms",
         "samples": 3, "mean": 433.333, "p75": 600.0, "poor_rate": 0.3333},
    ]


def test_timestamps_as_datetimes_in_another_time_zone_are_grouped_by_utc_date(monkeypatch):
    """psycopg devuelve datetimes en la zona de la sesión; el resultado no puede cambiar."""
    monkeypatch.setattr(analysis, "load_events", FakeLoader())
    from_text = analysis.events_per_day(START, END)
    madrid = timezone(timedelta(hours=1))
    monkeypatch.setattr(analysis, "load_events", FakeLoader(as_datetime=lambda text: datetime.fromisoformat(text).astimezone(madrid)))
    assert analysis.events_per_day(START, END) == from_text


def test_rows_without_a_dimension_are_dropped(monkeypatch):
    rows = [
        row("2026-11-05T08:00:00Z", "page_viewed", None, PAGE),  # sin sesión
        row("2026-11-05T08:00:00Z", "page_viewed", S1, {"route_template": "/"}),  # sin app
        row("2026-11-05T08:00:00Z", "web_vitals_measured", S1, {"app": "backoffice", "metric": "LCP", "value": 1.0}),
        row("2026-11-05T08:00:00Z", "frontend_error_occurred", S1, {"app": "backoffice", "route_template": "/"}),
    ]
    monkeypatch.setattr(analysis, "load_events", FakeLoader(rows))
    assert analysis.error_rate_per_day(START, END) == [
        {"date": "2026-11-05", "app": "backoffice", "sessions": 1, "sessions_with_errors": 1, "errors": 1, "error_rate": 1.0},
    ]
    assert analysis.web_vitals_per_day(START, END) == []
    assert analysis.frontend_errors_per_day(START, END) == []


def test_metrics_are_repeatable_and_json_serializable(loader):
    first = analysis.build_report(START, END)
    assert analysis.build_report(START, END) == first
    assert json.loads(json.dumps(first)) == first
    assert first["period"] == {"from": "2026-11-05T00:00:00Z", "to": "2026-11-07T00:00:00Z"}


def test_empty_period_gives_empty_lists(loader):
    empty = datetime(2026, 1, 1, tzinfo=timezone.utc)
    report = analysis.build_report(empty, empty + timedelta(days=1))
    assert report["metrics"] == {
        "events_per_day": [], "error_rate_per_day": [], "frontend_errors_per_day": [], "web_vitals_per_day": [],
    }


@pytest.mark.parametrize("name", ["events_per_day", "error_rate_per_day", "frontend_errors_per_day", "web_vitals_per_day"])
def test_metrics_do_not_use_python_loops(name):
    tree = ast.parse(inspect.getsource(getattr(analysis, name)))
    loops = (ast.For, ast.While, ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)
    assert not [node for node in ast.walk(tree) if isinstance(node, loops)]


def test_load_events_without_dsn_raises(monkeypatch):
    monkeypatch.delenv("TELEMETRY_READ_DATABASE_DSN", raising=False)
    with pytest.raises(analysis.TelemetryReportError, match="not configured"):
        analysis.load_events(["timestamp"], START, END)


# --- GET /telemetry/report ---------------------------------------------------

NOW = datetime(2026, 11, 6, 18, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(telemetry_router, "report_cache", TTLCache(60, clock=clock))
    monkeypatch.setattr(telemetry_router, "_now", lambda: NOW)
    return clock


@pytest.fixture
def builds(monkeypatch, clock):
    calls = []

    def build(start, end):
        calls.append((start, end))
        return analysis.build_report(start, end)

    monkeypatch.setattr(analysis, "load_events", FakeLoader())
    monkeypatch.setattr(telemetry_router, "build_report", build)
    return calls


async def get(**params):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/telemetry/report", params=params)


async def test_report_defaults_to_the_last_seven_days(builds):
    resp = await get()
    assert resp.status_code == 200
    assert builds == [(NOW - timedelta(days=7), NOW)]
    assert resp.json()["period"] == {"from": "2026-10-30T18:00:00Z", "to": "2026-11-06T18:00:00Z"}
    assert set(resp.json()["metrics"]) == {"events_per_day", "error_rate_per_day", "frontend_errors_per_day", "web_vitals_per_day"}


async def test_report_returns_the_metrics_for_the_requested_period(builds):
    resp = await get(start_date="2026-11-05T00:00:00Z", end_date="2026-11-07T00:00:00Z")
    assert resp.status_code == 200
    assert resp.json() == analysis.build_report(START, END)


@pytest.mark.parametrize("start_date", ["2026-11-05T01:00:00+01:00", "2026-11-05T00:00:00", "2026-11-05"])
async def test_dates_without_offset_are_utc_and_offsets_are_converted(builds, start_date):
    resp = await get(start_date=start_date, end_date="2026-11-07T00:00:00Z")
    assert resp.status_code == 200
    assert builds == [(START, END)]


async def test_only_start_date_ends_now_and_only_end_date_starts_seven_days_before(builds):
    assert (await get(start_date="2026-11-01T00:00:00Z")).status_code == 200
    assert (await get(end_date="2026-11-03T00:00:00Z")).status_code == 200
    assert builds == [
        (datetime(2026, 11, 1, tzinfo=timezone.utc), NOW),
        (datetime(2026, 10, 27, tzinfo=timezone.utc), datetime(2026, 11, 3, tzinfo=timezone.utc)),
    ]


async def test_same_period_within_60_seconds_is_served_from_cache(builds, clock):
    params = {"start_date": "2026-11-05T00:00:00Z", "end_date": "2026-11-07T00:00:00Z"}
    first = await get(**params)
    clock.now += 59.9
    assert (await get(**params)).json() == first.json()
    assert len(builds) == 1
    assert (await get(start_date="2026-11-05T01:00:00+01:00", end_date="2026-11-07T00:00:00Z")).status_code == 200
    assert len(builds) == 1  # mismo instante, otra notación
    await get(start_date="2026-11-04T00:00:00Z", end_date="2026-11-07T00:00:00Z")
    assert len(builds) == 2  # otra combinación
    clock.now += 0.1
    await get(**params)
    assert len(builds) == 3  # TTL cumplido


async def test_default_period_is_cached_too(builds, clock):
    await get()
    clock.now += 30
    await get()
    assert len(builds) == 1


@pytest.mark.parametrize("params, detail", [
    ({"start_date": "2026-11-07T00:00:00Z", "end_date": "2026-11-07T00:00:00Z"}, "start_date must be before end_date"),
    ({"start_date": "2026-11-08T00:00:00Z", "end_date": "2026-11-07T00:00:00Z"}, "start_date must be before end_date"),
    ({"start_date": "2026-11-07T00:00:00Z"}, "start_date must be before end_date"),
    ({"start_date": "2026-08-01T00:00:00Z", "end_date": "2026-11-01T00:00:00Z"}, "The period cannot exceed 90 days"),
])
async def test_invalid_period_returns_422_without_running_the_pipeline(builds, params, detail):
    resp = await get(**params)
    assert resp.status_code == 422
    assert resp.json() == {"detail": detail}
    assert builds == []


async def test_malformed_date_returns_422(builds):
    assert (await get(start_date="last week")).status_code == 422
    assert builds == []


async def test_storage_failure_returns_503_and_is_not_cached(monkeypatch, clock):
    monkeypatch.delenv("TELEMETRY_READ_DATABASE_DSN", raising=False)
    resp = await get()
    assert resp.status_code == 503
    assert resp.json() == {"detail": "Telemetry report unavailable"}
    monkeypatch.setattr(analysis, "load_events", FakeLoader())
    assert (await get()).status_code == 200
