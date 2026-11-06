"""Tests de los endpoints /reporting (services/reporting/router.py).

Los primeros sustituyen las funciones de data/pipelines o el cliente de
Prefect. Los de la base de datos solo se ejecutan si existen
``REPORTING_TEST_PIPELINE_DSN`` (login con ``reporting_writer``, para preparar
filas) y ``REPORTING_TEST_READER_DSN`` (login con ``reporting_reader``, el
que usa la API), sobre una base de test con las migraciones aplicadas.
"""
import os
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from prefect.client.schemas.objects import StateType

from data.pipelines.business_performance import config, entrypoints
from main import app

RUN_ID = "5c3d985c-feee-4bdb-9f31-0278286ffcfd"
NOW = datetime(2026, 11, 6, 4, 0, tzinfo=timezone.utc)


async def call(method: str, url: str, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, **kwargs)


def run_row(**overrides) -> dict:
    return {
        "run_id": RUN_ID, "flow_name": "business-performance", "trigger": "schedule", "requested_by": None,
        "window_start": date(2026, 10, 30), "window_end": date(2026, 11, 6), "started_at": NOW,
        "finished_at": NOW + timedelta(seconds=2), "duration_seconds": 2.0, "status": "completed",
        "failed_stage": None, "last_completed_date": date(2026, 11, 5), "events_extracted": 434,
        "events_deduplicated": 12, "events_invalid": 0, "rows_inserted": 84, "rows_updated": 0,
        "rows_unchanged": 0, "rows_deleted": 0, "late_days_detected": 0, "source_max_timestamp": NOW,
        "pipeline_version": "1.0.0", "error_class": None, "error_message": None, **overrides,
    }


@pytest.fixture
def development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")


# --- Estado y KPIs ----------------------------------------------------------------


async def test_status_returns_the_last_runs_and_kpi_statuses(monkeypatch):
    monkeypatch.setattr(entrypoints, "get_pipeline_status", lambda: {
        "last_run": run_row(), "last_completed_run": run_row(), "active_run": None,
        "latest_metric_date": date(2026, 11, 5), "latest_computed_at": NOW, "data_freshness_hours": 3.5,
        "kpis": [{"kpi": "shipments_total", "country": "US", "metric_date": date(2026, 11, 5),
                  "status": "not_instrumented"}],
    })
    response = await call("GET", "/reporting/pipeline/status")
    assert response.status_code == 200
    body = response.json()
    assert body["last_run"]["status"] == "completed"
    assert body["last_run"]["events_extracted"] == 434
    assert body["kpis"][0]["status"] == "not_instrumented"


@pytest.mark.parametrize("url", ["/reporting/pipeline/status", "/reporting/kpis", f"/reporting/pipeline/runs/{RUN_ID}"])
async def test_reads_answer_503_without_reporting_storage(monkeypatch, url):
    monkeypatch.delenv(config.READ_DSN_ENV, raising=False)
    response = await call("GET", url)
    assert response.status_code == 503
    assert response.json() == {"detail": "Reporting unavailable"}


async def test_unknown_run_is_404_and_a_malformed_id_is_422(monkeypatch):
    monkeypatch.setattr(entrypoints, "get_run", lambda run_id: None)
    assert (await call("GET", f"/reporting/pipeline/runs/{RUN_ID}")).status_code == 404
    assert (await call("GET", "/reporting/pipeline/runs/not-a-uuid")).status_code == 422


@pytest.mark.parametrize("query", [
    "granularity=month",
    "country=usa",
    "start_date=2026-11-06&end_date=2026-11-01",
    "start_date=2025-01-01&end_date=2026-11-01",
])
async def test_invalid_kpi_queries_are_422(query):
    assert (await call("GET", f"/reporting/kpis?{query}")).status_code == 422


# --- Disparo manual ---------------------------------------------------------------


async def test_manual_runs_are_disabled_outside_development_and_test(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(entrypoints, "trigger_run", lambda *args: pytest.fail("must not trigger"))
    response = await call("POST", "/reporting/pipeline/runs")
    assert response.status_code == 404


async def test_manual_run_is_scheduled_and_returns_its_run_id(development, monkeypatch):
    received = {}

    def trigger_run(window_start, window_end, requested_by):
        received.update(window_start=window_start, window_end=window_end, requested_by=requested_by)
        return {"run_id": RUN_ID, "status": "scheduled"}

    monkeypatch.setattr(entrypoints, "trigger_run", trigger_run)
    user = "usr_" + "a" * 32
    response = await call("POST", "/reporting/pipeline/runs",
                          json={"window_start": "2026-10-01", "window_end": "2026-10-08", "requested_by": user})
    assert response.status_code == 202
    assert response.json() == {"run_id": RUN_ID, "status": "scheduled"}
    assert received == {"window_start": date(2026, 10, 1), "window_end": date(2026, 10, 8), "requested_by": user}

    assert (await call("POST", "/reporting/pipeline/runs")).status_code == 202
    assert received == {"window_start": None, "window_end": None, "requested_by": None}


async def test_manual_run_is_409_with_the_active_run_id(development, monkeypatch):
    def trigger_run(*args):
        raise entrypoints.RunAlreadyActive(RUN_ID)

    monkeypatch.setattr(entrypoints, "trigger_run", trigger_run)
    response = await call("POST", "/reporting/pipeline/runs")
    assert response.status_code == 409
    assert response.json() == {"detail": "A pipeline run is already active", "run_id": RUN_ID}


@pytest.mark.parametrize("body", [
    {"window_start": "2026-10-01"},
    {"window_start": "2026-10-08", "window_end": "2026-10-01"},
    {"window_start": "2026-01-01", "window_end": "2026-06-01"},
    {"window_start": "2026-11-01", "window_end": "2099-01-01"},
    {"requested_by": "alice@example.com"},
    {"unexpected": True},
])
async def test_invalid_manual_runs_are_422(development, body):
    response = await call("POST", "/reporting/pipeline/runs", json=body)
    assert response.status_code == 422


async def test_manual_run_is_503_without_a_prefect_api(development, monkeypatch):
    monkeypatch.setattr(entrypoints, "PREFECT_API_URL", SimpleNamespace(value=lambda: None))
    response = await call("POST", "/reporting/pipeline/runs")
    assert response.status_code == 503


class FakeClient:
    def __init__(self, runs):
        self.runs = runs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read_deployment_by_name(self, name):
        assert name == "business-performance/business-performance-daily"
        return SimpleNamespace(id=uuid.UUID(int=1))

    def read_flow_runs(self, **kwargs):
        return self.runs


def flow_run(state_type, state_name, expected_start_time=None):
    return SimpleNamespace(id=uuid.uuid4(), state_type=state_type, state_name=state_name,
                           expected_start_time=expected_start_time)


def with_prefect(monkeypatch, runs):
    monkeypatch.setattr(entrypoints, "PREFECT_API_URL", SimpleNamespace(value=lambda: "http://prefect.test/api"))
    monkeypatch.setattr(entrypoints, "get_client", lambda sync_client: FakeClient(runs))
    calls = []

    def run_deployment(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=uuid.UUID(RUN_ID))

    monkeypatch.setattr(entrypoints, "run_deployment", run_deployment)
    return calls


def test_trigger_run_uses_run_deployment_without_waiting(monkeypatch):
    future = datetime.now(timezone.utc) + timedelta(hours=6)
    calls = with_prefect(monkeypatch, [flow_run(StateType.SCHEDULED, "Scheduled", future)])
    assert entrypoints.trigger_run() == {"run_id": RUN_ID, "status": "scheduled"}
    [kwargs] = calls
    assert (kwargs["timeout"], kwargs["as_subflow"]) == (0, False)
    assert kwargs["parameters"] == {"window_start": None, "window_end": None, "trigger": "manual",
                                    "requested_by": None}


@pytest.mark.parametrize("active", [
    flow_run(StateType.RUNNING, "Running"),
    flow_run(StateType.PENDING, "Pending"),
    flow_run(StateType.SCHEDULED, "AwaitingConcurrencySlot"),
    flow_run(StateType.SCHEDULED, "Scheduled", datetime.now(timezone.utc) - timedelta(seconds=5)),
])
def test_trigger_run_refuses_while_a_run_is_active_or_waiting(monkeypatch, active):
    calls = with_prefect(monkeypatch, [active])
    with pytest.raises(entrypoints.RunAlreadyActive) as error:
        entrypoints.trigger_run()
    assert error.value.run_id == str(active.id)
    assert calls == []


# --- Contra la base de datos de test ------------------------------------------------

PIPELINE_DSN = os.environ.get("REPORTING_TEST_PIPELINE_DSN")
READER_DSN = os.environ.get("REPORTING_TEST_READER_DSN")
needs_db = pytest.mark.skipif(
    not (PIPELINE_DSN and READER_DSN), reason="sin base de test de reporting (REPORTING_TEST_*_DSN)"
)


@pytest.fixture
def stored(monkeypatch):
    """Una corrida del futuro (la última para /status) y filas de KPI de una
    semana del siglo XVIII en el país ZZ, que el pipeline nunca escribe. Se
    borran al terminar."""
    monkeypatch.setenv(config.READ_DSN_ENV, READER_DSN)
    run_id = str(uuid.uuid4())
    monday = date(1700, 1, 4) + timedelta(weeks=random.randrange(0, 5_000))  # 4-1-1700 fue lunes
    rows = [
        ("on_time_delivery_rate", monday, "ups", 1, 2, "ok"),
        ("on_time_delivery_rate", monday, "fedex", 3, 3, "ok"),
        ("on_time_delivery_rate", monday + timedelta(days=1), "n/a", 0, 0, "no_activity"),
        ("shipments_total", monday, "ups", 4, None, "ok"),
        ("shipments_total", monday + timedelta(days=2), "n/a", 0, None, "capture_gap"),
    ]
    with psycopg.connect(PIPELINE_DSN) as connection:
        connection.execute(
            "insert into reporting.pipeline_runs (run_id, flow_name, trigger, window_start, window_end, started_at, "
            "finished_at, status, pipeline_version, events_extracted) values (%s, 'business-performance', 'manual', "
            "%s, %s, now() + interval '1 day', now() + interval '1 day 2 seconds', 'completed', '1.0.0', 9)",
            (run_id, monday, monday + timedelta(days=7)),
        )
        connection.execute(
            "insert into reporting.pipeline_run_days (run_id, metric_date, status, events_extracted, "
            "events_after_dedupe, rows_written, source_checksum, quality) values (%s, %s, 'loaded', 9, 9, 5, 'x', "
            "'{\"duplicates\": 0}')", (run_id, monday),
        )
        for kpi, day, carrier, numerator, denominator, status in rows:
            value = None if status not in ("ok", "no_activity") else (
                numerator / denominator if denominator else (numerator if denominator is None else None))
            connection.execute(
                "insert into reporting.executive_kpis_daily (kpi, metric_date, country, carrier, currency, numerator, "
                "denominator, value, unit, status, source_event_count, source_checksum, pipeline_version, run_id, "
                "computed_at) values (%s, %s, 'ZZ', %s, 'n/a', %s, %s, %s, 'u', %s, 0, 'x', '1.0.0', %s, now())",
                (kpi, day, carrier, numerator, denominator, value, status, run_id),
            )
    yield SimpleNamespace(run_id=run_id, monday=monday)
    with psycopg.connect(PIPELINE_DSN) as connection:
        connection.execute("delete from reporting.executive_kpis_daily where run_id = %s", (run_id,))
        connection.execute("delete from reporting.pipeline_run_days where run_id = %s", (run_id,))
        connection.execute("delete from reporting.pipeline_runs where run_id = %s", (run_id,))


def period(stored) -> str:
    return f"start_date={stored.monday}&end_date={stored.monday + timedelta(days=7)}&country=ZZ"


@needs_db
async def test_daily_kpis_are_returned_as_stored(stored):
    response = await call("GET", f"/reporting/kpis?{period(stored)}")
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 5
    first = rows[0]
    assert (first["kpi"], first["carrier"], first["numerator"], first["denominator"], first["value"]) == (
        "on_time_delivery_rate", "fedex", 3.0, 3.0, 1.0)
    assert (first["period_start"], first["period_end"], first["days_covered"]) == (
        stored.monday.isoformat(), (stored.monday + timedelta(days=1)).isoformat(), 1)


@needs_db
async def test_weekly_kpis_are_sum_over_sum(stored):
    response = await call("GET", f"/reporting/kpis?{period(stored)}&granularity=week")
    weeks = {row["kpi"]: row for row in response.json()["rows"]}
    rate = weeks["on_time_delivery_rate"]
    assert (rate["numerator"], rate["denominator"], rate["value"], rate["status"], rate["days_covered"]) == (
        4.0, 5.0, 0.8, "ok", 2)
    shipments = weeks["shipments_total"]
    assert (shipments["status"], shipments["value"]) == ("capture_gap", None)


@needs_db
async def test_run_detail_and_status_read_the_execution_log(stored):
    detail = (await call("GET", f"/reporting/pipeline/runs/{stored.run_id}")).json()
    assert (detail["status"], detail["events_extracted"], detail["duration_seconds"]) == ("completed", 9, 2.0)
    assert detail["days"][0]["quality"] == {"duplicates": 0}

    status = (await call("GET", "/reporting/pipeline/status")).json()
    assert status["last_run"]["run_id"] == stored.run_id
    assert status["last_completed_run"]["run_id"] == stored.run_id


@needs_db
async def test_the_api_role_cannot_write_reporting_tables():
    with psycopg.connect(READER_DSN) as connection, pytest.raises(psycopg.errors.InsufficientPrivilege):
        connection.execute("delete from reporting.pipeline_runs")
