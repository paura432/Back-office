"""Tests de POST /telemetry/events contra el contrato de docs/telemetry."""
import copy
from pathlib import Path

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient

from app.routers import telemetry as telemetry_router
from app.schemas.telemetry import CONTRACT, EVENT_MODELS, MAX_BATCH_EVENTS, TELEMETRY_EVENT_ADAPTER
from app.services import telemetry_store
from app.services.telemetry_store import TelemetryStoreError
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


class FakeStore:
    """Sustituye la escritura en BD: registra cada llamada y simula ON CONFLICT
    con los eventId que ya tenga guardados."""

    def __init__(self, existing=(), error=None):
        self.calls, self.existing, self.error = [], set(existing), error

    def __call__(self, rows):
        self.calls.append(rows)
        if self.error:
            raise self.error
        new = [row for row in rows if row["event_id"] not in self.existing]
        self.existing.update(row["event_id"] for row in new)
        return len(new)


@pytest.fixture
def store(monkeypatch):
    fake = FakeStore()
    monkeypatch.setattr(telemetry_router, "store_events", fake)
    return fake


async def post(client, payload):
    async with client as ac:
        return await ac.post("/telemetry/events", json=payload)


def stored_ids(store):
    return [row["event_id"] for rows in store.calls for row in rows]


async def test_valid_batch_is_stored_in_one_bulk_call(client, store):
    batch = FRONTEND_BATCH + [event("inventory_movement_recorded", 4)]
    resp = await post(client, {"events": batch})
    assert resp.status_code == 200
    assert resp.json() == {"received": 4, "stored": 4, "rejected": 0}
    assert len(store.calls) == 1
    assert stored_ids(store) == [e["eventId"] for e in batch]


def test_row_mapping_keeps_envelope_and_business_dimensions():
    page = telemetry_store.to_row(TELEMETRY_EVENT_ADAPTER.validate_python(FRONTEND_BATCH[0]))
    movement = telemetry_store.to_row(TELEMETRY_EVENT_ADAPTER.validate_python(event("inventory_movement_recorded", 4)))
    assert page == {
        "event_id": FRONTEND_BATCH[0]["eventId"],
        "event_type": "page_viewed",
        "timestamp": "2026-10-26T09:15:02.120Z",
        "service": "backoffice",
        "session_id": FRONTEND_BATCH[0]["sessionId"],
        "user_id": None,
        "request_id": None,
        "tags": {**FRONTEND_BATCH[0]["properties"], "schemaVersion": "1.0.0"},
    }
    assert movement["service"] == "backend"
    assert movement["tags"] == {"sku": "DEMO-BOX-001", "warehouse": "zaragoza", "quantity_delta": -3,
                                "quantity_after": 5, "schemaVersion": "1.0.0"}


async def test_empty_batch_returns_zeros_without_writing(client, store):
    resp = await post(client, {"events": []})
    assert resp.status_code == 200
    assert resp.json() == {"received": 0, "stored": 0, "rejected": 0}
    assert stored_ids(store) == []


async def test_full_batch_of_100_uses_a_single_write(client, store):
    resp = await post(client, {"events": [event(n=i) for i in range(MAX_BATCH_EVENTS)]})
    assert resp.json() == {"received": 100, "stored": 100, "rejected": 0}
    assert len(store.calls) == 1 and len(store.calls[0]) == 100


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
async def test_invalid_event_is_rejected_alone(client, store, change):
    bad = copy.deepcopy(FRONTEND_BATCH[0])
    change(bad)
    resp = await post(client, {"events": [FRONTEND_BATCH[1], bad]})
    assert resp.status_code == 200
    assert resp.json() == {"received": 2, "stored": 1, "rejected": 1}
    assert stored_ids(store) == [FRONTEND_BATCH[1]["eventId"]]


@pytest.mark.parametrize("properties", [{"quantity_delta": 0}, {"quantity_after": -1}, {"quantity_delta": 1.5}])
async def test_numeric_constraints(client, store, properties):
    resp = await post(client, {"events": [event("inventory_movement_recorded", **properties)]})
    assert resp.json() == {"received": 1, "stored": 0, "rejected": 1}


async def test_mixed_batch_counts_each_outcome(client, store):
    bad = copy.deepcopy(FRONTEND_BATCH[0])
    bad["properties"]["email"] = "a@b.c"
    resp = await post(client, {"events": [*FRONTEND_BATCH, bad, "not an event", None, 42, []]})
    assert resp.json() == {"received": 8, "stored": 3, "rejected": 5}
    assert stored_ids(store) == [e["eventId"] for e in FRONTEND_BATCH]


async def test_all_invalid_batch_does_not_write(client, store):
    resp = await post(client, {"events": [{"eventId": "x"}, {}]})
    assert resp.json() == {"received": 2, "stored": 0, "rejected": 2}
    assert stored_ids(store) == []


async def test_duplicate_event_id_in_batch_is_stored_once(client, store):
    resp = await post(client, {"events": [FRONTEND_BATCH[0], FRONTEND_BATCH[0], FRONTEND_BATCH[1]]})
    assert resp.json() == {"received": 3, "stored": 2, "rejected": 0}
    assert stored_ids(store) == [FRONTEND_BATCH[0]["eventId"], FRONTEND_BATCH[1]["eventId"]]


async def test_already_stored_event_is_not_counted_as_stored(client, store):
    store.existing.add(FRONTEND_BATCH[0]["eventId"])
    resp = await post(client, {"events": FRONTEND_BATCH})
    assert resp.json() == {"received": 3, "stored": 2, "rejected": 0}


async def test_storage_failure_returns_503_without_counters(client, monkeypatch):
    failing = FakeStore(error=TelemetryStoreError("telemetry storage write failed"))
    monkeypatch.setattr(telemetry_router, "store_events", failing)
    resp = await post(client, {"events": FRONTEND_BATCH})
    assert resp.status_code == 503
    assert resp.json() == {"detail": "Telemetry storage unavailable"}
    assert len(failing.calls) == 1


async def test_missing_storage_configuration_returns_503(client, monkeypatch):
    monkeypatch.delenv("TELEMETRY_DATABASE_DSN", raising=False)
    resp = await post(client, {"events": FRONTEND_BATCH})
    assert resp.status_code == 503


def test_database_error_is_wrapped_without_dsn(monkeypatch):
    dsn = "postgresql://writer:secret@db.invalid/postgres"
    monkeypatch.setenv("TELEMETRY_DATABASE_DSN", dsn)

    def refuse(*_args, **_kwargs):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(telemetry_store.psycopg, "connect", refuse)
    with pytest.raises(TelemetryStoreError) as excinfo:
        telemetry_store.store_events([{"event_id": "x"}])
    assert "secret" not in str(excinfo.value) and dsn not in str(excinfo.value)


def test_store_sends_the_whole_batch_in_one_statement(monkeypatch):
    executed = []

    class Cursor:
        rowcount = 2

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params):
            executed.append((query, params))

    class Connection(Cursor):
        def cursor(self):
            return Cursor()

    monkeypatch.setenv("TELEMETRY_DATABASE_DSN", "postgresql://local")
    monkeypatch.setattr(telemetry_store.psycopg, "connect", lambda *_a, **_k: Connection())
    assert telemetry_store.store_events([{"event_id": "a"}, {"event_id": "b"}]) == 2
    assert len(executed) == 1
    assert "on conflict do nothing" in executed[0][0]
    assert executed[0][1] == ('[{"event_id": "a"}, {"event_id": "b"}]',)


@pytest.mark.parametrize("payload", [
    {},
    {"events": {}},
    {"events": [], "extra": True},
    {"events": [event(n=i) for i in range(MAX_BATCH_EVENTS + 1)]},
    [FRONTEND_BATCH[0]],
], ids=["sin events", "events no lista", "campo extra", "lote demasiado grande", "cuerpo es una lista"])
async def test_invalid_batch_shape_rejects_whole_request(client, store, payload):
    assert (await post(client, payload)).status_code == 422
    assert store.calls == []


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


# ── inventory_movement_recorded desde POST /inventory/movements ──────────

MOVEMENT_RESULT = {
    "sku": "DEMO-BOX-001", "name": "Shipping box", "description": "Synthetic", "warehouse": "zaragoza",
    "quantity": 37, "low_stock_threshold": 10, "last_updated": "2026-10-26T19:40:01.123456+00:00",
}


@pytest.fixture
def inventory_router(monkeypatch):
    from app.routers import inventory

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INVENTORY_DEMO_ENABLED", "true")
    monkeypatch.setattr(inventory, "register_inventory_movement", lambda movement: dict(MOVEMENT_RESULT))
    return inventory


async def post_movement(client, delta, headers=None):
    async with client as ac:
        return await ac.post("/inventory/movements", headers=headers or {},
                             json={"sku": "DEMO-BOX-001", "warehouse": "zaragoza", "quantity_delta": delta})


async def test_movement_emits_contract_event_after_commit(client, inventory_router, monkeypatch):
    rows = []
    monkeypatch.setattr(telemetry_store, "store_events", lambda batch: rows.extend(batch) or len(batch))
    request_id = "3d2c1b0a-9f8e-4d7c-a6b5-4c3d2e1f0a9b"
    resp = await post_movement(client, -3, {"X-Request-Id": request_id})
    assert resp.status_code == 201 and resp.json()["quantity"] == 37
    assert len(rows) == 1
    row = rows[0]
    assert (row["event_type"], row["service"], row["session_id"], row["user_id"], row["request_id"]) == (
        "inventory_movement_recorded", "backend", None, None, request_id)
    assert row["timestamp"] == "2026-10-26T19:40:01.123Z"
    assert row["tags"] == {"sku": "DEMO-BOX-001", "warehouse": "zaragoza", "quantity_delta": -3,
                           "quantity_after": 37, "schemaVersion": "1.0.0"}
    TELEMETRY_EVENT_ADAPTER.validate_python({
        "eventId": row["event_id"], "timestamp": row["timestamp"], "sessionId": None, "userId": None,
        "event_type": row["event_type"], "schemaVersion": "1.0.0", "requestId": row["request_id"],
        "properties": {k: v for k, v in row["tags"].items() if k != "schemaVersion"},
    })


@pytest.mark.parametrize("header", [None, "not-a-uuid", "00000000-0000-0000-0000-000000000000"])
async def test_movement_creates_request_id_when_header_is_missing_or_invalid(client, inventory_router, monkeypatch, header):
    rows = []
    monkeypatch.setattr(telemetry_store, "store_events", lambda batch: rows.extend(batch) or len(batch))
    await post_movement(client, 5, {"X-Request-Id": header} if header else None)
    assert rows[0]["request_id"] != header
    assert telemetry_store.UUID_PATTERN.match(rows[0]["request_id"])


@pytest.mark.parametrize("error", [TelemetryStoreError("telemetry storage write failed"), RuntimeError("boom")])
async def test_telemetry_failure_does_not_affect_the_movement(client, inventory_router, monkeypatch, error):
    def fail(_batch):
        raise error

    monkeypatch.setattr(telemetry_store, "store_events", fail)
    resp = await post_movement(client, 5)
    assert resp.status_code == 201
    assert resp.json()["quantity"] == 37


@pytest.mark.parametrize("exception, status_code", [("InventoryItemNotFound", 404), ("InsufficientInventory", 409)])
async def test_rejected_movement_emits_nothing(client, inventory_router, monkeypatch, exception, status_code):
    from app.services import demo_inventory

    def reject(_movement):
        raise getattr(demo_inventory, exception)

    rows = []
    monkeypatch.setattr(inventory_router, "register_inventory_movement", reject)
    monkeypatch.setattr(telemetry_store, "store_events", lambda batch: rows.extend(batch) or len(batch))
    resp = await post_movement(client, -500)
    assert resp.status_code == status_code
    assert rows == []
