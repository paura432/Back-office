"""Los subflows se ejecutan por separado, con sus entradas y salidas
explícitas, sin base de datos.

Prefect corre en un servidor temporal (``prefect_test_harness``); los eventos
son los de ``kpi_events.py``. La extracción y la carga necesitan PostgreSQL y
se prueban en ``test_pipeline_flow.py``.
"""
from datetime import datetime, timedelta, timezone

import pytest
from prefect.client.orchestration import get_client
from prefect.testing.utilities import prefect_test_harness

from data.pipelines import pipeline
from tests.pipelines.kpi_events import (
    DAY,
    SEEN_LONG_AGO,
    all_alive,
    compute,
    created,
    delivered,
    frame,
    ordered,
    returned,
    survey,
)

END = DAY + timedelta(days=2)


@pytest.fixture(scope="module", autouse=True)
def prefect_server():
    with prefect_test_harness():
        yield


def business_events() -> list[dict]:
    return [
        ordered(DAY - timedelta(days=4), 100, "ES"),
        created(DAY, 1), created(DAY, 1, hour=12), created(DAY, 2, "ES", "seur"),
        delivered(DAY, 1, shipping_cost=8.0, currency="USD", weight_kg=2.0),
        delivered(DAY + timedelta(days=1), 2, "ES", "seur", on_time=False, shipping_cost=6.0, currency="EUR",
                  weight_kg=1.0),
        returned(DAY + timedelta(days=1), 1, order_id=100),
        survey(DAY, 4), survey(DAY + timedelta(days=1), 5, country="ES"),
    ]


def source(events: list[dict]) -> pipeline.KpiSourceEvents:
    return pipeline.KpiSourceEvents(window_start=DAY, window_end=END, instrumented_since=SEEN_LONG_AGO,
                                    events=frame(events), heartbeat=all_alive(DAY, DAY + timedelta(days=1)))


def test_transformation_subflow_runs_on_its_own_and_matches_the_pure_functions():
    events = business_events()
    kpis = pipeline.compute_executive_kpis(source(events))
    expected = compute(events, end=END)
    assert kpis.rows == expected["rows"]
    assert kpis.days == expected["days"]
    assert kpis.totals == expected["totals"]
    # 6 KPIs x 2 países x 2 días: 7 medidas el lunes (envíos US y ES, y el
    # resto en US) y 5 el martes (todo en ES salvo envíos); el resto es un día
    # sin actividad con los productores emitiendo.
    assert kpis.status_counts == {"no_activity": 12, "ok": 12}


def test_subflow_parameters_keep_the_business_events_out_of_prefect():
    events = business_events()
    state = pipeline.compute_executive_kpis(source(events), return_state=True)
    with get_client(sync_client=True) as client:
        parameters = client.read_flow_run(state.state_details.flow_run_id).parameters
    assert parameters == {"source": {
        "window_start": DAY.isoformat(),
        "window_end": END.isoformat(),
        "late_days_detected": 0,
        "instrumented_since": SEEN_LONG_AGO,
        "event_count": len(events),
    }}


def test_quality_subflow_runs_on_its_own():
    events = business_events()
    kpis = pipeline.compute_executive_kpis(source(events))
    quality = pipeline.check_executive_kpi_quality(source(events), kpis, datetime(2026, 3, 5, tzinfo=timezone.utc))
    assert sorted(quality) == [DAY.isoformat(), (DAY + timedelta(days=1)).isoformat()]
    assert quality[DAY.isoformat()]["duplicates"] == 1
