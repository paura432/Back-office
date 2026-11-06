"""Tests del flow completo contra PostgreSQL real (Supabase local, base de test).

Solo se ejecutan si existen ``REPORTING_TEST_PIPELINE_DSN`` (login miembro de
``telemetry_reader`` y ``reporting_writer``) y ``REPORTING_TEST_ADMIN_DSN``
(rol con BYPASSRLS para sembrar ``telemetry_events``), sobre una base
``telemetry_test`` con las migraciones aplicadas. Prefect corre en un servidor
temporal (``prefect_test_harness``).

``telemetry_events`` no admite borrados, así que cada test usa una semana
pasada al azar y transportistas con un prefijo propio: las filas de KPI por
transportista son solo suyas aunque otra ejecución haya usado los mismos días.
"""
import os
import random
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import psycopg
import pytest
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import FlowRunFilter, FlowRunFilterId
from prefect.testing.utilities import prefect_test_harness
from psycopg.rows import dict_row

from data.pipelines import pipeline
from data.pipelines.business_performance import config, storage, synthetic
from data.process import business_kpis

PIPELINE_DSN = os.environ.get("REPORTING_TEST_PIPELINE_DSN")
ADMIN_DSN = os.environ.get("REPORTING_TEST_ADMIN_DSN")

pytestmark = pytest.mark.skipif(
    not (PIPELINE_DSN and ADMIN_DSN), reason="sin base de test de reporting (REPORTING_TEST_*_DSN)"
)


@pytest.fixture(scope="module", autouse=True)
def prefect_server():
    with prefect_test_harness():
        yield


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv(config.SOURCE_DSN_ENV, PIPELINE_DSN)
    monkeypatch.setenv(config.REPORTING_DSN_ENV, PIPELINE_DSN)
    monkeypatch.setenv(config.EVAL_DIR_ENV, str(tmp_path / "runs"))
    return tmp_path


class Seeded:
    """Semana sembrada: ventana [start, end), eventos y prefijo de transportista."""

    def __init__(self):
        self.start = date(1800, 1, 6) + timedelta(weeks=random.randrange(0, 11_000))
        self.end = self.start + timedelta(days=7)
        self.prefix = "t" + uuid.uuid4().hex[:8]
        events = synthetic.generate_events(self.start - timedelta(days=3), self.end, seed=random.randrange(1, 9_000))
        for event in events:
            if "carrier" in event["tags"]:
                event["tags"]["carrier"] = f"{self.prefix}_{event['tags']['carrier']}"
        self.events = events
        insert(events)

    def expected_shipments(self) -> dict[tuple[str, str, str], int]:
        """Envíos por (día, país, transportista) contados aquí, sin el código del
        pipeline: cada shipment_id el primer día que aparece."""
        first_seen = {}
        for event in sorted(self.events, key=lambda e: (e["timestamp"], e["event_id"])):
            if event["event_type"] == "shipment_created":
                first_seen.setdefault(event["tags"]["shipment_id"], event)
        counts = defaultdict(int)
        for event in first_seen.values():
            day = event["timestamp"][:10]
            if self.start.isoformat() <= day < self.end.isoformat():
                counts[(day, event["tags"]["destination_country"], event["tags"]["carrier"])] += 1
        return dict(counts)


def insert(events: list[dict]) -> None:
    with psycopg.connect(ADMIN_DSN) as connection:
        connection.execute(synthetic.INSERT, (psycopg.types.json.Jsonb(events),))


@pytest.fixture
def seeded(env):
    return Seeded()


def run(seeded: Seeded, **kwargs):
    return pipeline.business_performance_flow(
        window_start=seeded.start, window_end=seeded.end, trigger="manual", return_state=True, **kwargs
    )


def query(sql: str, params=None) -> list[dict]:
    with psycopg.connect(ADMIN_DSN, row_factory=dict_row) as connection:
        return connection.execute(sql, params or {}).fetchall()


def run_row(state) -> dict:
    [row] = query("select * from reporting.pipeline_runs where run_id = %s", (state.state_details.flow_run_id,))
    return row


def carrier_rows(seeded: Seeded, kpi: str = "shipments_total") -> dict[tuple[str, str, str], dict]:
    rows = query(
        "select * from reporting.executive_kpis_daily where kpi = %s and carrier like %s",
        (kpi, f"{seeded.prefix}_%"),
    )
    return {(row["metric_date"].isoformat(), row["country"], row["carrier"]): row for row in rows}


def task_states(state) -> dict[str, str]:
    with get_client(sync_client=True) as client:
        task_runs = client.read_task_runs(
            flow_run_filter=FlowRunFilter(id=FlowRunFilterId(any_=[state.state_details.flow_run_id]))
        )
    return {task_run.name.rsplit("-", 1)[0]: task_run.state_name for task_run in task_runs}


def test_run_loads_the_kpis_and_logs_its_metadata(seeded, env):
    state = run(seeded)
    assert state.is_completed()

    log = run_row(state)
    assert (log["status"], log["trigger"], log["failed_stage"], log["error_class"]) == ("completed", "manual", None, None)
    assert (log["window_start"], log["window_end"]) == (seeded.start, seeded.end)
    assert log["started_at"] <= log["finished_at"]
    assert log["events_extracted"] > 0 and log["rows_inserted"] > 0
    assert log["last_completed_date"] == seeded.end - timedelta(days=1)

    days = query("select * from reporting.pipeline_run_days where run_id = %s order by metric_date",
                 (log["run_id"],))
    assert [day["metric_date"] for day in days] == business_kpis.days_between(seeded.start, seeded.end)
    assert all(day["status"] == "loaded" and "events_by_service_hour" in day["quality"] for day in days)

    shipments = carrier_rows(seeded)
    assert {key: int(row["numerator"]) for key, row in shipments.items()} == seeded.expected_shipments()
    assert {row["status"] for row in shipments.values()} == {"ok"}
    assert all(row["run_id"] == log["run_id"] and row["revision"] == 1 for row in shipments.values())

    assert (env / "runs" / f"{log['run_id']}.json").exists()


def test_second_run_changes_nothing_and_reuses_the_cached_transformation(seeded):
    first = run_row(run(seeded))
    second_state = run(seeded)
    second = run_row(second_state)
    assert (second["rows_inserted"], second["rows_updated"], second["rows_deleted"]) == (0, 0, 0)
    assert second["rows_unchanged"] == first["rows_inserted"]
    assert task_states(second_state)["transform_kpis"] == "Cached"
    assert {row["run_id"] for row in carrier_rows(seeded).values()} == {first["run_id"]}
    assert query("select count(*) as n from reporting.executive_kpis_daily_history where carrier like %s",
                 (f"{seeded.prefix}_%",))[0]["n"] == 0


def test_late_event_updates_the_figure_and_keeps_the_published_version(seeded):
    first = run_row(run(seeded))
    day = seeded.start + timedelta(days=2)
    carrier = f"{seeded.prefix}_ups"
    before = carrier_rows(seeded)[(day.isoformat(), "US", carrier)]

    late = synthetic.generate_events(day, day + timedelta(days=1), seed=random.randrange(9_000, 99_999))
    late = [event for event in late if event["event_type"] == "shipment_created"][:1]
    late[0]["tags"] |= {"carrier": carrier, "destination_country": "US"}
    insert(late)
    current = storage.day_fingerprints(PIPELINE_DSN, seeded.start, seeded.end)
    loaded = storage.loaded_fingerprints(PIPELINE_DSN, seeded.start, seeded.end)
    assert [d for d in business_kpis.days_between(seeded.start, seeded.end) if current[d] != loaded[d]] == [day]

    second = run_row(run(seeded))
    after = carrier_rows(seeded)[(day.isoformat(), "US", carrier)]
    assert (after["numerator"], after["revision"], after["run_id"]) == (before["numerator"] + 1, 2, second["run_id"])
    [old] = query(
        "select * from reporting.executive_kpis_daily_history where kpi = 'shipments_total' and metric_date = %s "
        "and carrier = %s", (day, carrier),
    )
    assert (old["operation"], old["numerator"], old["run_id"], old["replaced_by_run_id"]) == (
        "UPDATE", before["numerator"], first["run_id"], second["run_id"],
    )
    assert storage.day_fingerprints(PIPELINE_DSN, day, day + timedelta(days=1)) == \
        storage.loaded_fingerprints(PIPELINE_DSN, day, day + timedelta(days=1))


def failing_on(day: date, error: Exception, times: int = 10**6):
    """Sustituto de storage.load_day que falla ``times`` veces al llegar a ``day``."""
    original = storage.load_day
    calls = {"failures": 0}

    def load_day(connection, run_id, day_summary, rows, quality):
        if day_summary["metric_date"] == day.isoformat() and calls["failures"] < times:
            calls["failures"] += 1
            raise error
        return original(connection, run_id, day_summary, rows, quality)

    return load_day, calls


def test_a_failed_load_is_completed_by_the_next_run_without_duplicates(seeded, monkeypatch):
    fourth = seeded.start + timedelta(days=3)
    originals = storage.load_day, pipeline.load_kpis
    load_day, _ = failing_on(fourth, psycopg.OperationalError("connection lost"))
    monkeypatch.setattr(storage, "load_day", load_day)
    monkeypatch.setattr(pipeline, "load_kpis", pipeline.load_kpis.with_options(retries=0))

    failed_state = run(seeded)
    assert failed_state.is_failed()
    failed = run_row(failed_state)
    assert (failed["status"], failed["failed_stage"], failed["error_class"]) == ("failed", "load", "OperationalError")
    assert failed["error_message"] == "OperationalError (sqlstate n/a)"
    assert failed["last_completed_date"] == fourth - timedelta(days=1)

    monkeypatch.setattr(storage, "load_day", originals[0])
    monkeypatch.setattr(pipeline, "load_kpis", originals[1])
    retried = run_row(run(seeded))
    assert retried["status"] == "completed"
    assert retried["rows_unchanged"] > 0 and retried["rows_inserted"] > 0
    shipments = carrier_rows(seeded)
    assert {key: int(row["numerator"]) for key, row in shipments.items()} == seeded.expected_shipments()
    assert {row["revision"] for row in shipments.values()} == {1}


def test_transient_errors_are_retried_and_data_errors_are_not(seeded, monkeypatch):
    load_day, calls = failing_on(seeded.start, psycopg.OperationalError("connection lost"), times=1)
    monkeypatch.setattr(storage, "load_day", load_day)
    monkeypatch.setattr(pipeline, "load_kpis", pipeline.load_kpis.with_options(retries=1, retry_delay_seconds=0))
    assert run(seeded).is_completed() and calls["failures"] == 1

    load_day, calls = failing_on(seeded.start, psycopg.errors.DataError("bad value"), times=1)
    monkeypatch.setattr(storage, "load_day", load_day)
    state = run(seeded)
    assert state.is_failed() and calls["failures"] == 1
    log = run_row(state)
    assert (log["failed_stage"], log["error_class"]) == ("load", "DataError")
    [day] = query("select status from reporting.pipeline_run_days where run_id = %s", (log["run_id"],))
    assert day["status"] == "failed"


def test_optional_steps_can_fail_without_stopping_the_run(seeded, env, monkeypatch):
    def broken_quality(*args, **kwargs):
        raise RuntimeError("quality check exploded")

    monkeypatch.setattr(business_kpis, "quality_by_day", broken_quality)
    (env / "not-a-directory").write_text("")
    monkeypatch.setenv(config.EVAL_DIR_ENV, str(env / "not-a-directory" / "runs"))

    state = run(seeded)
    assert state.is_completed()
    states = task_states(state)
    assert (states["check_quality"], states["export_eval_snapshot"]) == ("Failed", "Failed")
    log = run_row(state)
    assert log["status"] == "completed"
    qualities = query("select quality from reporting.pipeline_run_days where run_id = %s", (log["run_id"],))
    assert all("quality check exploded" in row["quality"]["unavailable"] for row in qualities)


def test_run_is_skipped_while_another_run_holds_the_lock(seeded):
    with psycopg.connect(PIPELINE_DSN, autocommit=True) as holder:
        holder.execute("select pg_advisory_lock(%s)", (config.LOCK_KEY,))
        state = run(seeded)
        holder.execute("select pg_advisory_unlock(%s)", (config.LOCK_KEY,))
    assert state.is_cancelled()
    log = run_row(state)
    assert log["status"] == "skipped" and "lock held" in log["error_message"]
    assert carrier_rows(seeded) == {}


def test_orphaned_running_rows_are_marked_as_crashed(seeded):
    orphan = str(uuid.uuid4())
    with psycopg.connect(PIPELINE_DSN) as connection:
        storage.insert_run(connection, run_id=orphan, trigger="manual", requested_by=None,
                           window_start=seeded.start, window_end=seeded.end, status="running")
    assert run(seeded).is_completed()
    [row] = query("select status, finished_at from reporting.pipeline_runs where run_id = %s", (orphan,))
    assert row["status"] == "crashed" and row["finished_at"] is not None


def test_explicit_windows_are_validated_before_registering_the_run(env):
    today = datetime.now(timezone.utc).date()
    with pytest.raises(config.InvalidWindow):
        pipeline.business_performance_flow(window_start=today, window_end=today + timedelta(days=5))
