"""Tests de las funciones puras de data/process/business_kpis.py: dedupe,
monedas, estados, ventana, calidad y agregado semanal. Sin base de datos."""
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from data.process import business_kpis as bk
from tests.pipelines.kpi_events import (
    COLUMNS,
    DAY,
    SEEN_LONG_AGO,
    all_alive,
    at,
    compute,
    created,
    delivered,
    event,
    heartbeat,
    pick,
)


def test_same_shipment_sent_twice_counts_once_on_its_first_day():
    nxt = DAY + timedelta(days=1)
    result = compute([created(DAY, 1), created(nxt, 1, hour=9), created(nxt, 2)], end=DAY + timedelta(days=2))
    assert [row["value"] for row in pick(result, "shipments_total", carrier="ups")] == [1.0]
    assert [row["value"] for row in pick(result, "shipments_total", nxt, carrier="ups")] == [1.0]
    assert [day["events_deduplicated"] for day in result["days"]] == [0, 1]
    assert result["totals"]["events_deduplicated"] == 1


def test_duplicate_of_an_event_before_the_window_is_not_counted_again():
    result = compute([created(DAY - timedelta(days=3), 1), created(DAY, 1)])
    assert pick(result, "shipments_total")[0]["status"] == "no_activity"
    assert result["days"][0]["events_deduplicated"] == 1


def test_events_missing_a_required_property_are_invalid_and_excluded():
    broken = event("shipment_created", at(DAY), shipment_id=9, order_id=9, destination_country="US")  # sin carrier
    result = compute([broken, created(DAY, 1)])
    assert result["totals"]["events_invalid"] == 1
    assert [row["numerator"] for row in pick(result, "shipments_total", carrier="ups")] == [1.0]


def test_costs_are_stored_per_currency_and_never_added_together():
    result = compute([
        delivered(DAY, 1, shipping_cost=10.0, currency="USD", weight_kg=2.0),
        delivered(DAY, 2, shipping_cost=5.5, currency="USD", weight_kg=0.5),
        delivered(DAY, 3, shipping_cost=7.0, currency="EUR", weight_kg=1.0),
    ])
    totals = {row["currency"]: row["value"] for row in pick(result, "shipping_cost_total")}
    assert totals == {"USD": 15.5, "EUR": 7.0}
    per_kg = {row["currency"]: (row["numerator"], row["denominator"], row["value"], row["unit"])
              for row in pick(result, "shipping_cost_per_kg")}
    assert per_kg == {"USD": (15.5, 2.5, 6.2, "USD/kg"), "EUR": (7.0, 1.0, 7.0, "EUR/kg")}


def test_deliveries_without_cost_make_the_cost_kpis_a_capture_gap_not_a_zero():
    result = compute([delivered(DAY, 1)])
    for kpi in ("shipping_cost_total", "shipping_cost_per_kg"):
        [row] = pick(result, kpi)
        assert (row["status"], row["value"]) == ("capture_gap", None)
    assert pick(result, "on_time_delivery_rate")[0]["status"] == "ok"


def test_on_time_rate_keeps_numerator_and_denominator():
    result = compute([delivered(DAY, 1), delivered(DAY, 2, on_time=False), delivered(DAY, 3)])
    [row] = pick(result, "on_time_delivery_rate")
    assert (row["numerator"], row["denominator"], row["value"], row["unit"]) == (2.0, 3.0, 0.666667, "ratio")
    assert row["source_event_count"] == 3


def test_return_country_comes_from_the_order_then_the_shipment_else_unknown():
    events = [
        event("order_created", at(DAY - timedelta(days=5)), order_id=100, customer_id=1, item_count=1,
              ingestion_channel="api", destination_country="ES"),
        created(DAY - timedelta(days=5), 200, country="US"),  # order_id 200, sin order_created
        event("return_requested", at(DAY), return_id=1, order_id=100, sku="A", quantity=1, reason_code="other"),
        event("return_requested", at(DAY), return_id=2, order_id=200, sku="A", quantity=1, reason_code="other"),
        event("return_requested", at(DAY), return_id=3, order_id=999, sku="A", quantity=1, reason_code="other"),
    ]
    result = compute(events)
    numerators = {row["country"]: row["numerator"] for row in result["rows"] if row["kpi"] == "return_rate"}
    assert numerators == {"ES": 1.0, "US": 1.0, "unknown": 1.0}


def test_return_rate_without_returns_is_zero_only_if_the_backend_was_alive():
    alive = compute([delivered(DAY, 1)], beat=all_alive(DAY))
    assert [(row["status"], row["value"]) for row in pick(alive, "return_rate")] == [("ok", 0.0)]
    silent = compute([delivered(DAY, 1)], beat=heartbeat(("integration", DAY, 15)))
    assert [(row["status"], row["value"]) for row in pick(silent, "return_rate")] == [("capture_gap", None)]


def test_status_when_there_are_no_source_events():
    never = compute([], seen={event_type: None for event_type in bk.SOURCE_EVENT_TYPES})
    assert {row["status"] for row in never["rows"]} == {"not_instrumented"}
    assert {row["value"] for row in never["rows"]} == {None}

    later = compute([], seen={**SEEN_LONG_AGO, "shipment_created": at(DAY + timedelta(days=1))})
    assert pick(later, "shipments_total")[0]["status"] == "not_instrumented"

    quiet = compute([])
    [count] = pick(quiet, "shipments_total")
    [rate] = pick(quiet, "on_time_delivery_rate")
    assert (count["status"], count["value"]) == ("no_activity", 0.0)
    assert (rate["status"], rate["numerator"], rate["denominator"], rate["value"]) == ("no_activity", 0.0, 0.0, None)

    gap = compute([], beat=heartbeat(("integration", DAY, 3)))
    assert pick(gap, "shipments_total")[0]["status"] == "capture_gap"
    assert pick(gap, "on_time_delivery_rate")[0]["status"] == "no_activity"


def test_every_kpi_day_and_expected_country_has_a_row():
    result = compute([created(DAY, 1, country="FR", carrier="dhl")], end=DAY + timedelta(days=3))
    keys = {(row["kpi"], row["metric_date"], row["country"]) for row in result["rows"]}
    for kpi in bk.KPIS:
        for day in bk.days_between(DAY, DAY + timedelta(days=3)):
            assert {(kpi, day.isoformat(), "US"), (kpi, day.isoformat(), "ES")} <= keys
    assert pick(result, "shipments_total", country="FR")[0]["value"] == 1.0


def test_checksums_identify_the_events_behind_each_row_and_day():
    first, second = created(DAY, 1), created(DAY, 2, carrier="ups")
    result = compute([first, second])
    [row] = pick(result, "shipments_total")
    assert row["source_checksum"] == bk.checksum([first["event_id"], second["event_id"]])
    assert result["days"][0]["source_checksum"] == bk.checksum([second["event_id"], first["event_id"]])
    assert pick(result, "shipments_total", country="ES")[0]["source_checksum"] == bk.EMPTY_CHECKSUM


def test_result_does_not_depend_on_the_order_of_the_input():
    events = [delivered(DAY, n, shipping_cost=1.1 * n, currency="USD", weight_kg=0.7 * n) for n in range(1, 30)]
    events += [created(DAY, n) for n in range(1, 30)] + [created(DAY, 5, hour=12)]
    assert compute(events) == compute(list(reversed(events)))


def test_plan_window_is_the_last_seven_days_when_nothing_changed():
    today = date(2026, 3, 20)
    day = today - timedelta(days=20)
    plan = bk.plan_window({day: "a"}, {day: "a"}, today, 35, 7)
    assert (plan["window_start"], plan["window_end"], plan["late_days"]) == (today - timedelta(days=7), today, 0)


def test_plan_window_reaches_back_to_a_loaded_day_that_changed():
    today = date(2026, 3, 20)
    day = today - timedelta(days=20)
    plan = bk.plan_window({day: "new"}, {day: "old"}, today, 35, 7)
    assert (plan["window_start"], plan["late_days"]) == (day, 1)


def test_plan_window_includes_days_with_events_that_were_never_loaded():
    today = date(2026, 3, 20)
    day = today - timedelta(days=12)
    plan = bk.plan_window({day: "a"}, {}, today, 35, 7)
    assert (plan["window_start"], plan["late_days"]) == (day, 0)


def test_quality_flags_future_timestamps_and_compares_with_the_median():
    events = [created(DAY - timedelta(days=offset), offset) for offset in range(1, 8)]
    events += [created(DAY, 100, hour=9), created(DAY, 101, hour=23)]
    run_started_at = datetime(DAY.year, DAY.month, DAY.day, 12, tzinfo=timezone.utc)
    frame = pd.DataFrame(events, columns=COLUMNS)
    result = compute(events)
    quality = bk.quality_by_day(frame, all_alive(DAY), result["days"], DAY, DAY + timedelta(days=1), run_started_at)
    day = quality[DAY.isoformat()]
    assert (day["source_events"], day["median_source_events_prev_7d"], day["volume_ratio_vs_median"]) == (2, 1.0, 2.0)
    assert day["future_timestamps"] == 1
    assert day["events_by_service_hour"]["backend"] == {"00": 1}


def kpi_row(kpi, day, status="ok", numerator=0.0, denominator=None, currency="n/a", carrier="n/a", revision=1):
    return {"kpi": kpi, "metric_date": day, "country": "US", "carrier": carrier, "currency": currency,
            "numerator": numerator, "denominator": denominator, "status": status, "revision": revision,
            "computed_at": datetime(2026, 3, 10, tzinfo=timezone.utc)}


def test_weekly_aggregate_is_sum_over_sum_across_days_and_carriers():
    rows = [
        kpi_row("on_time_delivery_rate", DAY, numerator=1, denominator=1, carrier="ups"),
        kpi_row("on_time_delivery_rate", DAY, numerator=0, denominator=3, carrier="fedex"),
        kpi_row("on_time_delivery_rate", DAY + timedelta(days=1), "no_activity", 0, 0),
        kpi_row("on_time_delivery_rate", DAY + timedelta(days=6), numerator=4, denominator=4, revision=2),
    ]
    [week] = bk.aggregate_weekly(rows)
    assert (week["numerator"], week["denominator"], week["value"]) == (5.0, 8.0, 0.625)
    assert (week["status"], week["days_covered"], week["revision"], week["carrier"]) == ("ok", 3, 2, "all")
    assert (week["period_start"], week["period_end"]) == (DAY, DAY + timedelta(days=7))


def test_weekly_value_is_null_when_a_day_could_not_be_measured():
    rows = [kpi_row("shipments_total", DAY, numerator=5, carrier="ups"),
            kpi_row("shipments_total", DAY + timedelta(days=1), "capture_gap")]
    [week] = bk.aggregate_weekly(rows)
    assert (week["status"], week["value"]) == ("capture_gap", None)


@pytest.mark.parametrize("statuses, expected", [
    (["no_activity", "ok"], "ok"),
    (["no_activity", "no_activity"], "no_activity"),
    (["ok", "capture_gap"], "capture_gap"),
    (["capture_gap", "not_instrumented"], "not_instrumented"),
])
def test_combine_status_keeps_the_most_severe(statuses, expected):
    assert bk.combine_status(statuses) == expected


def test_weekly_costs_stay_per_currency():
    rows = [kpi_row("shipping_cost_total", DAY, numerator=10, currency="USD"),
            kpi_row("shipping_cost_total", DAY, numerator=3, currency="EUR"),
            kpi_row("shipping_cost_total", DAY + timedelta(days=1), "no_activity")]
    weeks = {week["currency"]: (week["value"], week["unit"]) for week in bk.aggregate_weekly(rows)}
    assert weeks == {"EUR": (3.0, "EUR"), "USD": (10.0, "USD")}
