"""Tests de POST /telemetry/events contra el contrato de docs/telemetry."""
import copy
import json
import logging
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.schemas.telemetry import CONTRACT, EVENT_MODELS, MAX_BATCH_EVENTS
from main import app

DOCS_CONTRACT = Path(__file__).resolve().parents[3] / "docs" / "telemetry" / "event-schemas.json"


def event(event_type="page_viewed", n=0, **properties):
    defaults = {
        "page_viewed": {"app": "backoffice", "route_template": "/", "viewport_class": "desktop"},
        "inventory_movement_recorded": {"sku": "DEMO-BOX-001", "warehouse": "zaragoza", "quantity_delta": -3, "quantity_after": 5},
    }
    return {
        "eventId": f"6f1c2a3e-8b4d-4c1e-9f2a-{n:012x}",
        "timestamp": "2026-10-26T09:15:02.120Z",
        "sessionId": "0b8e7d6c-5a4b-4c3d-8e2f-1a0b9c8d7e6f",
        "userId": None,
        "event_type": event_type,
        "schemaVersion": "1.0.0",
        "requestId": None,
        "properties": {**defaults.get(event_type, {}), **properties},
    }


FRONTEND_BATCH = [
    event("page_viewed", 1, referrer_type="direct", locale="es-ES"),
    event("frontend_error_occurred", 2, app="backoffice", route_template="/", error_kind="fetch_failed",
          http_status=500, error_fingerprint="0123456789abcdef"),
    event("web_vitals_measured", 3, app="backoffice", route_template="/", metric="LCP", value=812.4,
          rating="good", viewport_class="desktop"),
]


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def post(client, payload):
    async with client as ac:
        return await ac.post("/telemetry/events", json=payload)


def telemetry_logs(caplog):
    return [r.getMessage() for r in caplog.records if r.name == "trackflow.telemetry"]


async def test_valid_batch_returns_received_count(client, caplog):
    caplog.set_level(logging.INFO, logger="trackflow.telemetry")
    resp = await post(client, {"events": FRONTEND_BATCH + [event("inventory_movement_recorded", 4)]})
    assert resp.status_code == 200
    assert resp.json() == {"received": 4}
    logged = [json.loads(line.split(" ", 1)[1]) for line in telemetry_logs(caplog)]
    assert [e["eventId"] for e in logged] == [e["eventId"] for e in FRONTEND_BATCH] + [event(n=4)["eventId"]]


async def test_empty_batch_is_accepted_with_zero(client, caplog):
    caplog.set_level(logging.INFO, logger="trackflow.telemetry")
    resp = await post(client, {"events": []})
    assert resp.status_code == 200
    assert resp.json() == {"received": 0}
    assert telemetry_logs(caplog) == []


def mutate(path, value):
    def apply(e):
        target = e
        *parents, key = path
        for p in parents:
            target = target[p]
        if value is KeyError:
            del target[key]
        else:
            target[key] = value
    return apply


INVALID = {
    "propiedad fuera de allowlist": mutate(["properties", "email"], "a@b.c"),
    "propiedad requerida ausente": mutate(["properties", "app"], KeyError),
    "enum inválido": mutate(["properties", "viewport_class"], "watch"),
    "tipo incorrecto": mutate(["properties", "app"], 1),
    "event_type desconocido": mutate(["event_type"], "foo_bar"),
    "campo extra en sobre": mutate(["source"], "web"),
    "campo nullable ausente": mutate(["sessionId"], KeyError),
    "timestamp sin Z": mutate(["timestamp"], "2026-10-26T09:15:02+02:00"),
    "timestamp imposible": mutate(["timestamp"], "2026-13-45T09:15:02Z"),
    "eventId no UUID": mutate(["eventId"], "abc"),
    "userId no seudónimo": mutate(["userId"], "user@example.com"),
    "schemaVersion distinta": mutate(["schemaVersion"], "2.0.0"),
    "route_template con query": mutate(["properties", "route_template"], "/?q=x"),
}


@pytest.mark.parametrize("change", INVALID.values(), ids=INVALID.keys())
async def test_invalid_event_rejects_whole_batch_and_logs_nothing(client, caplog, change):
    caplog.set_level(logging.INFO, logger="trackflow.telemetry")
    bad = copy.deepcopy(FRONTEND_BATCH[0])
    change(bad)
    resp = await post(client, {"events": [FRONTEND_BATCH[1], bad]})
    assert resp.status_code == 422
    assert telemetry_logs(caplog) == []


@pytest.mark.parametrize("properties", [{"quantity_delta": 0}, {"quantity_after": -1}, {"quantity_delta": 1.5}])
async def test_numeric_constraints(client, properties):
    resp = await post(client, {"events": [event("inventory_movement_recorded", **properties)]})
    assert resp.status_code == 422


@pytest.mark.parametrize("payload", [
    {},
    {"events": {}},
    {"events": [], "extra": True},
    {"events": [FRONTEND_BATCH[0], FRONTEND_BATCH[0]]},
    {"events": [event(n=i) for i in range(MAX_BATCH_EVENTS + 1)]},
], ids=["sin events", "events no lista", "campo extra", "eventId duplicado", "lote demasiado grande"])
async def test_invalid_batch_shape(client, payload):
    assert (await post(client, payload)).status_code == 422


async def test_non_json_body_is_rejected(client):
    async with client as ac:
        resp = await ac.post("/telemetry/events", content=b"not json", headers={"content-type": "application/json"})
    assert resp.status_code == 422


def test_models_match_contract_allowlists():
    events = CONTRACT["$defs"]["events"]
    assert set(EVENT_MODELS) == set(events) == set(CONTRACT["properties"]["event_type"]["enum"])
    for name, model in EVENT_MODELS.items():
        props = model.model_fields["properties"].annotation.model_fields
        assert set(props) == set(events[name]["properties"])
        assert {k for k, f in props.items() if f.is_required()} == set(events[name]["required"])


@pytest.mark.skipif(not DOCS_CONTRACT.exists(), reason="docs/ no está montado (contenedor api)")
def test_api_contract_copy_is_identical_to_docs():
    copy_path = Path(__file__).resolve().parents[1] / "app" / "schemas" / "event-schemas.json"
    assert copy_path.read_bytes() == DOCS_CONTRACT.read_bytes()
