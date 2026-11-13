"""Eventos de telemetría en memoria para los tests del pipeline.

Cada evento tiene la forma de una fila de ``public.telemetry_events``
(``event_id``, ``event_type``, ``timestamp``, ``service``, ``tags``) y sus
``tags`` siguen ``docs/telemetry/event-schemas.json``: las mismas propiedades,
tipos y productor (``service``) que el contrato. No hay base de datos ni
servidor de Prefect detrás.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from data.process import business_kpis as bk

DAY = date(2026, 3, 2)  # lunes
SEEN_LONG_AGO = {event_type: "2026-01-01T00:00:00+00:00" for event_type in bk.SOURCE_EVENT_TYPES}
COLUMNS = ["event_id", "event_type", "timestamp", "service", "tags"]
COUNTRIES = ("US", "ES")


def at(day: date, hour: int = 10, minute: int = 0) -> str:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc).isoformat()


def event(event_type: str, moment: str, event_id: str | None = None, **tags) -> dict:
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": moment,
        "service": bk.SOURCE_EVENTS[event_type].producer,
        "tags": {**tags, "schemaVersion": "1.0.0"},
    }


def created(day: date, shipment_id: int, country: str = "US", carrier: str = "ups", hour: int = 10, **extra) -> dict:
    """``shipment_created``; el pedido tiene el mismo número que el envío."""
    return event("shipment_created", at(day, hour), shipment_id=shipment_id, order_id=shipment_id, carrier=carrier,
                 origin_warehouse="los-angeles", destination_country=country, weight_kg=1.0, **extra)


def delivered(day: date, shipment_id: int, country: str = "US", carrier: str = "ups", on_time: bool = True,
              **extra) -> dict:
    return event("shipment_delivered", at(day, 15), shipment_id=shipment_id, carrier=carrier,
                 destination_country=country, on_time=on_time, transit_hours=24, **extra)


def ordered(day: date, order_id: int, country: str) -> dict:
    return event("order_created", at(day, 8), order_id=order_id, customer_id=1, item_count=1,
                 ingestion_channel="api", destination_country=country)


def returned(day: date, return_id: int, order_id: int) -> dict:
    return event("return_requested", at(day, 11), return_id=return_id, order_id=order_id, sku="SKU-100",
                 quantity=1, reason_code="damaged")


def survey(day: date, score, country: str | None = "US") -> dict:
    tags = {"score": score, "segment": "b2c", "context": "delivery"}
    if country is not None:
        tags["country"] = country
    return event("customer_satisfaction_submitted", at(day, 18), **tags)


def frame(events: list[dict]) -> pd.DataFrame:
    """Filas tal como las devuelve ``storage.extract_source_events``."""
    return pd.DataFrame(events, columns=COLUMNS)


def heartbeat(*entries) -> pd.DataFrame:
    """(service, día, hora) con un evento."""
    return pd.DataFrame(
        [{"service": service, "hour": pd.Timestamp(at(day, hour)), "events": 1} for service, day, hour in entries],
        columns=["service", "hour", "events"],
    )


def all_alive(*days: date) -> pd.DataFrame:
    """Latido de todos los productores de eventos fuente esos días."""
    producers = {spec.producer for spec in bk.SOURCE_EVENTS.values()}
    return heartbeat(*[(producer, day, 0) for producer in producers for day in days])


def compute(events, start=DAY, end=None, beat=None, seen=SEEN_LONG_AGO, countries=COUNTRIES) -> dict:
    """La transformación completa con las funciones puras, en el mismo orden
    que el subflow ``compute_executive_kpis`` (``test_subflows.py`` comprueba
    que dan lo mismo)."""
    end = end or start + timedelta(days=1)
    beat = all_alive(*bk.days_between(start, end)) if beat is None else beat
    prepared = bk.prepare_kpi_events(frame(events), start, end)
    clean = prepared["events"]
    measured = [
        *bk.shipments_total_rows(clean),
        *bk.on_time_delivery_rate_rows(clean),
        *bk.shipping_cost_total_rows(clean),
        *bk.shipping_cost_per_kg_rows(clean),
        *bk.return_rate_rows(clean, beat),
        *bk.customer_satisfaction_avg_rows(clean),
    ]
    rows = bk.assign_statuses(measured, clean, beat, seen, start, end, countries)
    return {"rows": rows, "days": bk.count_kpi_rows(prepared["days"], rows), "totals": prepared["totals"]}


def pick(result_or_rows, kpi: str, day: date = DAY, country: str = "US", **match) -> list[dict]:
    rows = result_or_rows["rows"] if isinstance(result_or_rows, dict) else result_or_rows
    return [
        row for row in rows
        if row["kpi"] == kpi and row["metric_date"] == day.isoformat() and row["country"] == country
        and all(row[key] == value for key, value in match.items())
    ]
