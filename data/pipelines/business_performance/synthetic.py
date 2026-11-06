"""Eventos de negocio sintéticos para probar el pipeline (PIPELINE_DESIGN.md §8).

Hoy no se emite ningún evento fuente de los KPIs, así que el pipeline se prueba
con estos eventos. Siguen el contrato ``docs/telemetry/event-schemas.json``
(propiedades obligatorias y allowlist) y tienen la forma de las filas de
``public.telemetry_events``. Incluyen los casos que el pipeline debe resolver:
el mismo envío enviado dos veces con otro ``eventId``, entregas sin coste,
devoluciones y encuestas sin país.

Son deterministas: el mismo periodo y la misma semilla dan los mismos
``event_id`` (uuid5), así que volver a insertarlos no duplica nada.

    uv run --project data/pipelines python -m data.pipelines.business_performance.synthetic \\
        --start 2026-10-24 --end 2026-11-06 --dsn-env REPORTING_TEST_ADMIN_DSN \\
        --jsonl data/raw/business_performance/synthetic_events.jsonl

Solo inserta en una base de datos llamada ``telemetry_test``.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import psycopg

NAMESPACE = uuid.UUID("5b0c7a52-0f2e-4f55-9a4b-6a0d3f1c2e71")
SCHEMA_VERSION = "1.0.0"
TEST_DATABASE = "telemetry_test"
MARKETS = {
    # país: (transportistas, almacén de origen, moneda)
    "US": (("ups", "fedex", "dhl"), "los-angeles", "USD"),
    "ES": (("mrw", "seur", "dhl"), "zaragoza", "EUR"),
}
SERVICES = {
    "order_created": "backend",
    "shipment_created": "backend",
    "shipment_delivered": "integration",
    "return_requested": "backend",
    "customer_satisfaction_submitted": "frontend",
}

INSERT = """
insert into public.telemetry_events
  (event_id, event_type, "timestamp", service, session_id, user_id, request_id, tags)
select event_id, event_type, "timestamp", service, session_id, user_id, request_id, tags
from jsonb_to_recordset(%s::jsonb) as e(
  event_id uuid, event_type text, "timestamp" timestamptz, service text,
  session_id uuid, user_id text, request_id uuid, tags jsonb
)
on conflict do nothing
"""


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def generate_events(start: date, end: date, seed: int = 7) -> list[dict]:
    """Eventos de ``[start, end)``. Envíos creados cada día en EE. UU. y
    España; entregas, devoluciones y encuestas solo si caen dentro del
    periodo."""
    rng = random.Random(f"{seed}:{start}:{end}")
    limit = datetime.combine(end, time.min, tzinfo=timezone.utc)
    next_id = start.toordinal() * 10_000 + seed * 1_000_000_000
    events: list[dict] = []

    def add(event_type: str, moment: datetime, properties: dict, *, session: bool = False) -> None:
        if moment >= limit:
            return
        events.append({
            "event_id": str(uuid.uuid5(NAMESPACE, f"{seed}:{start}:{end}:{len(events)}")),
            "event_type": event_type,
            "timestamp": _iso(moment),
            "service": SERVICES[event_type],
            "session_id": str(uuid.uuid5(NAMESPACE, f"session:{len(events)}")) if session else None,
            "user_id": None,
            "request_id": str(uuid.uuid5(NAMESPACE, f"request:{seed}:{start}:{len(events)}")),
            "tags": {**properties, "schemaVersion": SCHEMA_VERSION},
        })

    day = start
    while day < end:
        for country, (carriers, warehouse, currency) in MARKETS.items():
            for _ in range(rng.randint(6, 12)):
                next_id += 1
                order_id = shipment_id = next_id
                created_at = datetime.combine(day, time(rng.randint(6, 20), rng.randint(0, 59)), tzinfo=timezone.utc)
                carrier = rng.choice(carriers)
                weight = round(rng.uniform(0.3, 12.0), 2)
                add("order_created", created_at - timedelta(minutes=rng.randint(10, 90)), {
                    "order_id": order_id, "customer_id": rng.randint(1, 40), "item_count": rng.randint(1, 4),
                    "ingestion_channel": rng.choice(["api", "email", "manual"]), "destination_country": country,
                })
                shipment = {
                    "shipment_id": shipment_id, "order_id": order_id, "carrier": carrier,
                    "origin_warehouse": warehouse, "destination_country": country, "weight_kg": weight,
                }
                add("shipment_created", created_at, shipment)
                if rng.random() < 0.08:  # el mismo envío reenviado con otro eventId
                    add("shipment_created", created_at + timedelta(minutes=rng.randint(2, 30)), shipment)

                delivered_at = created_at + timedelta(hours=rng.randint(20, 72))
                delivery = {
                    "shipment_id": shipment_id, "carrier": carrier, "destination_country": country,
                    "on_time": rng.random() < 0.86,
                    "transit_hours": round((delivered_at - created_at).total_seconds() / 3600, 1),
                    "weight_kg": weight,
                }
                if rng.random() > 0.05:  # algunas entregas llegan sin coste
                    delivery |= {"shipping_cost": round(rng.uniform(4.5, 38.0), 2), "currency": currency}
                add("shipment_delivered", delivered_at, delivery)

                if rng.random() < 0.2:
                    add("return_requested", delivered_at + timedelta(days=rng.randint(1, 4)), {
                        "return_id": order_id + 500_000, "order_id": order_id, "sku": f"SKU-{rng.randint(100, 999)}",
                        "quantity": 1, "reason_code": rng.choice(["damaged", "wrong_item", "no_longer_needed"]),
                    })
                if rng.random() < 0.3:
                    survey = {"score": rng.choices([1, 2, 3, 4, 5], [1, 1, 2, 5, 6])[0], "segment": "b2c",
                              "context": "delivery"}
                    if rng.random() > 0.1:  # alguna encuesta llega sin país
                        survey["country"] = country
                    add("customer_satisfaction_submitted", delivered_at + timedelta(hours=rng.randint(1, 30)),
                        survey, session=True)
        day += timedelta(days=1)
    return sorted(events, key=lambda event: (event["timestamp"], event["event_id"]))


def insert_events(dsn: str, events: list[dict]) -> int:
    """Inserta en ``telemetry_test`` y devuelve cuántos eran nuevos."""
    with psycopg.connect(dsn, connect_timeout=3) as connection:
        database = connection.execute("select current_database()").fetchone()[0]
        if database != TEST_DATABASE:
            raise SystemExit(f"Refusing to insert synthetic events into '{database}' (only {TEST_DATABASE})")
        return connection.execute(INSERT, (json.dumps(events),)).rowcount


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eventos de negocio sintéticos para telemetry_test")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True, help="Excluido")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--dsn-env", help="Variable de entorno con el DSN de telemetry_test")
    parser.add_argument("--jsonl", type=Path, help="Copia de los eventos generados (data/raw/...)")
    args = parser.parse_args(argv)
    events = generate_events(args.start, args.end, args.seed)
    if args.jsonl:
        args.jsonl.parent.mkdir(parents=True, exist_ok=True)
        args.jsonl.write_text("".join(json.dumps(event) + "\n" for event in events))
    inserted = insert_events(os.environ[args.dsn_env], events) if args.dsn_env else 0
    print(json.dumps({"generated": len(events), "inserted": inserted}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
