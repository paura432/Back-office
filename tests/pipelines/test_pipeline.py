"""Tests unitarios de las tasks de transformación de data/pipelines/pipeline.py.

Cada test llama a la función de la task (``task.fn``) con eventos en memoria
con la forma de las filas de ``telemetry_events`` y del contrato
``docs/telemetry/event-schemas.json`` (``kpi_events.py``): sin base de datos,
sin servidor de Prefect y sin APIs externas. Los valores esperados están
calculados a mano con la definición de cada KPI de PIPELINE_DESIGN.md §2.2.

    uv run --project data/pipelines python -m pytest tests/pipelines/test_pipeline.py
"""
from datetime import timedelta

import pandas as pd
import pytest

from data.pipelines import pipeline
from tests.pipelines.kpi_events import (
    DAY,
    SEEN_LONG_AGO,
    all_alive,
    created,
    delivered,
    frame,
    heartbeat,
    ordered,
    pick,
    returned,
    survey,
)

NEXT_DAY = DAY + timedelta(days=1)
KPI_TASKS = (
    pipeline.compute_shipments_total,
    pipeline.compute_on_time_delivery_rate,
    pipeline.compute_shipping_cost_total,
    pipeline.compute_shipping_cost_per_kg,
    pipeline.compute_customer_satisfaction_avg,
)


def prepare(events: list[dict], start=DAY, end=NEXT_DAY) -> dict:
    return pipeline.prepare_kpi_events.fn(frame(events), start, end)


def values(rows: list[dict]) -> dict[tuple, tuple]:
    """(país, transportista, moneda) -> (numerador, denominador, valor, unidad)."""
    return {
        (row["country"], row["carrier"], row["currency"]): (row["numerator"], row["denominator"], row["value"],
                                                              row["unit"])
        for row in rows
    }


# --- Valores conocidos, calculados a mano ---------------------------------------


def test_shipments_total_counts_each_shipment_once_per_day_country_and_carrier():
    first = created(DAY, 1, hour=9)
    resent = created(DAY, 1, hour=11)  # el mismo envío con otro eventId
    events = [first, resent, created(DAY, 2), created(DAY, 3, carrier="fedex"), created(DAY, 4, "ES", "seur")]
    prepared = prepare(events)
    assert prepared["totals"]["events_deduplicated"] == 1
    assert resent["event_id"] not in set(prepared["events"]["event_id"])

    # US/ups: envíos 1 y 2 -> 2; US/fedex: envío 3 -> 1; ES/seur: envío 4 -> 1
    assert values(pipeline.compute_shipments_total.fn(prepared["events"])) == {
        ("ES", "seur", "n/a"): (1.0, None, 1.0, "shipments"),
        ("US", "fedex", "n/a"): (1.0, None, 1.0, "shipments"),
        ("US", "ups", "n/a"): (2.0, None, 2.0, "shipments"),
    }


def test_on_time_delivery_rate_is_on_time_deliveries_over_deliveries():
    events = [delivered(DAY, 1), delivered(DAY, 2), delivered(DAY, 3), delivered(DAY, 4, on_time=False)]
    rows = pipeline.compute_on_time_delivery_rate.fn(prepare(events)["events"])
    # 3 de 4 entregas a tiempo: 3 / 4 = 0.75
    assert values(rows) == {("US", "ups", "n/a"): (3.0, 4.0, 0.75, "ratio")}


def test_shipping_cost_total_and_per_kg_follow_their_definition_per_currency():
    events = [
        delivered(DAY, 1, shipping_cost=12.5, currency="USD", weight_kg=2.0),
        delivered(DAY, 2, shipping_cost=7.5, currency="USD", weight_kg=3.0),
        delivered(DAY, 3, "ES", "seur", shipping_cost=9.0, currency="EUR", weight_kg=1.5),
        delivered(DAY, 4),  # sin coste: no entra en ninguno de los dos KPIs de coste
    ]
    clean = prepare(events)["events"]
    # US: 12.5 + 7.5 = 20.0 USD; ES: 9.0 EUR. Nunca se suman monedas distintas.
    assert values(pipeline.compute_shipping_cost_total.fn(clean)) == {
        ("ES", "seur", "EUR"): (9.0, None, 9.0, "EUR"),
        ("US", "ups", "USD"): (20.0, None, 20.0, "USD"),
    }
    # US: 20.0 USD / (2.0 + 3.0) kg = 4.0 USD/kg; ES: 9.0 EUR / 1.5 kg = 6.0 EUR/kg
    assert values(pipeline.compute_shipping_cost_per_kg.fn(clean)) == {
        ("ES", "seur", "EUR"): (9.0, 1.5, 6.0, "EUR/kg"),
        ("US", "ups", "USD"): (20.0, 5.0, 4.0, "USD/kg"),
    }


def test_return_rate_is_returns_over_deliveries_of_the_same_day_and_country():
    events = [
        ordered(DAY - timedelta(days=3), 100, "ES"),  # el país de la devolución sale del pedido
        *[delivered(DAY, shipment_id, "ES", "seur") for shipment_id in (11, 12, 13, 14)],
        returned(DAY, 1, order_id=100),
    ]
    rows = pipeline.compute_return_rate.fn(prepare(events)["events"], all_alive(DAY))
    # 1 devolución / 4 entregas en España = 0.25
    assert values(rows) == {("ES", "n/a", "n/a"): (1.0, 4.0, 0.25, "ratio")}


def test_customer_satisfaction_avg_is_the_mean_score_per_country():
    events = [survey(DAY, 5), survey(DAY, 4), survey(DAY, 3), survey(DAY, 2, country=None)]
    rows = pipeline.compute_customer_satisfaction_avg.fn(prepare(events)["events"])
    # US: (5 + 4 + 3) / 3 = 4.0; la encuesta sin país va a "unknown"
    assert values(rows) == {
        ("US", "n/a", "n/a"): (12.0, 3.0, 4.0, "score_1_5"),
        ("unknown", "n/a", "n/a"): (2.0, 1.0, 2.0, "score_1_5"),
    }


def test_assign_kpi_statuses_never_turns_missing_data_into_a_zero():
    clean = prepare([])["events"]

    def statuses(beat, seen=SEEN_LONG_AGO):
        return pipeline.assign_kpi_statuses.fn([], clean, beat, seen, DAY, NEXT_DAY)

    [quiet] = pick(statuses(all_alive(DAY)), "shipments_total")
    assert (quiet["status"], quiet["value"]) == ("no_activity", 0.0)  # el backend emitió otros eventos ese día

    [silent] = pick(statuses(heartbeat(("integration", DAY, 3))), "shipments_total")
    assert (silent["status"], silent["value"]) == ("capture_gap", None)  # el backend no emitió nada

    never = statuses(all_alive(DAY), seen=dict.fromkeys(SEEN_LONG_AGO))
    assert {(row["status"], row["value"]) for row in never} == {("not_instrumented", None)}
    assert len(never) == 6 * 2  # seis KPIs x dos países esperados


# --- Entradas inválidas o mal formadas ----------------------------------------


@pytest.mark.parametrize("broken", [
    pytest.param(delivered(DAY, 2, on_time="yes"), id="on_time como texto"),
    pytest.param(delivered(DAY, 2, on_time=None), id="on_time nulo"),
    pytest.param(delivered(DAY, None), id="shipment_id nulo"),
    pytest.param(delivered(DAY, "abc"), id="shipment_id no numérico"),
    pytest.param(delivered(DAY, 2.5), id="shipment_id decimal"),
    pytest.param(delivered(DAY, 2, country="usa"), id="país fuera de ISO 3166"),
    pytest.param(delivered(DAY, 2, carrier=None), id="transportista nulo"),
])
def test_deliveries_that_break_the_contract_are_discarded_not_counted_as_late(broken):
    prepared = prepare([delivered(DAY, 1), broken])
    assert prepared["totals"]["events_invalid"] == 1
    [row] = pipeline.compute_on_time_delivery_rate.fn(prepared["events"])
    assert (row["numerator"], row["denominator"], row["value"]) == (1.0, 1.0, 1.0)


def test_malformed_costs_and_weights_stay_out_of_the_cost_kpis():
    events = [
        delivered(DAY, 1, shipping_cost=10.0, currency="USD", weight_kg=2.0),
        delivered(DAY, 2, shipping_cost="free", currency="USD", weight_kg=1.0),
        delivered(DAY, 3, shipping_cost=-4.0, currency="USD", weight_kg=1.0),
        delivered(DAY, 4, shipping_cost=6.0, currency="GBP", weight_kg=1.0),
        delivered(DAY, 5, shipping_cost=5.0, currency="USD", weight_kg=0),
    ]
    prepared = prepare(events)
    clean = prepared["events"]
    # Coste y peso son opcionales en shipment_delivered: la entrega es válida y
    # cuenta para la tasa a tiempo, pero solo entran en el coste los valores
    # que cumplen el contrato (coste >= 0, moneda USD o EUR, peso > 0).
    assert prepared["totals"]["events_invalid"] == 0
    assert pick(pipeline.compute_on_time_delivery_rate.fn(clean), "on_time_delivery_rate")[0]["denominator"] == 5.0
    assert values(pipeline.compute_shipping_cost_total.fn(clean)) == {("US", "ups", "USD"): (15.0, None, 15.0, "USD")}
    assert values(pipeline.compute_shipping_cost_per_kg.fn(clean)) == {("US", "ups", "USD"): (10.0, 2.0, 5.0, "USD/kg")}


def test_survey_scores_outside_one_to_five_are_invalid():
    events = [survey(DAY, 5), survey(DAY, 9), survey(DAY, "4"), survey(DAY, True), survey(DAY, 0)]
    prepared = prepare(events)
    assert prepared["totals"]["events_invalid"] == 4
    [row] = pipeline.compute_customer_satisfaction_avg.fn(prepared["events"])
    assert (row["numerator"], row["denominator"], row["value"]) == (5.0, 1.0, 5.0)


def test_unreadable_timestamps_and_tags_make_the_event_invalid():
    unreadable_time = {**created(DAY, 2), "timestamp": "yesterday"}
    tags_as_text = {**created(DAY, 3), "tags": "shipment_id=3"}
    no_tags = {**created(DAY, 4), "tags": None}
    prepared = prepare([created(DAY, 1), unreadable_time, tags_as_text, no_tags])
    # El evento sin fecha legible no pertenece a ningún día de la ventana; los
    # otros dos se cuentan como inválidos en su día.
    assert prepared["totals"]["events_invalid"] == 2
    assert values(pipeline.compute_shipments_total.fn(prepared["events"])) == {
        ("US", "ups", "n/a"): (1.0, None, 1.0, "shipments"),
    }


def test_rows_without_the_telemetry_events_columns_are_rejected():
    rows = pd.DataFrame([created(DAY, 1)]).drop(columns=["tags"])
    with pytest.raises(ValueError, match="missing columns: tags"):
        pipeline.prepare_kpi_events.fn(rows, DAY, NEXT_DAY)


def test_kpi_tasks_return_no_measured_rows_for_a_window_without_events():
    clean = prepare([created(DAY - timedelta(days=2), 1)])["events"]  # solo un envío anterior a la ventana
    assert clean.empty
    assert [task.fn(clean) for task in KPI_TASKS] == [[]] * len(KPI_TASKS)
    assert pipeline.compute_return_rate.fn(clean, all_alive(DAY)) == []


# --- Caché -------------------------------------------------------------------


def test_cache_key_changes_with_new_events_or_window_but_not_with_their_order():
    events = [created(DAY, 1), created(DAY, 2)]

    def key(evs, end=NEXT_DAY):
        return pipeline.kpi_events_cache_key(None, {"events": frame(evs), "window_start": DAY, "window_end": end})

    assert key(events) == key(list(reversed(events)))
    assert key(events) != key([*events, created(DAY, 3)])  # un evento tardío obliga a recalcular
    assert key(events) != key(events, end=NEXT_DAY + timedelta(days=1))
