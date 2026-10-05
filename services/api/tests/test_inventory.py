"""
Tests for TrackFlow Inventory Manager — INV-T18.
Covers items, lots, stock calculation, and cosmetics creation.
INV-001–018, INV-025–033, INV-041–046.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from database_inventory import get_inventory_connection, init_inventory_db
from inventory_core import get_stock, get_items_with_stock
from main import app


# ──────────────────────── Fixtures ────────────────────────


@pytest.fixture(autouse=True)
def db():
    """Ensure clean inventory tables before each test."""
    conn = get_inventory_connection()
    init_inventory_db(conn)
    conn.execute("DELETE FROM stock_movements")
    conn.execute("DELETE FROM lots")
    conn.execute("DELETE FROM items")
    conn.execute("DELETE FROM inventory_metadata")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def client():
    """Return a TestClient with clean inventory DB per test."""
    return TestClient(app)


def _create_item_payload(**overrides):
    """Helper to build a minimal item payload."""
    payload = {
        "warehouse": "los_angeles",
        "client_name": "TestClient",
        "sku": "SKU-001",
        "name": "Test Item",
        "category": "fashion",
        "unit_of_measure": "unit",
        "reorder_point": 5.0,
    }
    payload.update(overrides)
    return payload


# ──────────────────────── INV-001: Warehouse ────────────────────────


class TestWarehouse:
    """INV-001: warehouse must be los_angeles or zaragoza."""

    def test_valid_warehouse_los_angeles(self, client):
        resp = client.post("/api/inventory/items", json=_create_item_payload(warehouse="los_angeles"))
        assert resp.status_code == 201
        assert resp.json()["warehouse"] == "los_angeles"

    def test_valid_warehouse_zaragoza(self, client):
        resp = client.post("/api/inventory/items", json=_create_item_payload(warehouse="zaragoza"))
        assert resp.status_code == 201
        assert resp.json()["warehouse"] == "zaragoza"

    def test_invalid_warehouse(self, client):
        resp = client.post("/api/inventory/items", json=_create_item_payload(warehouse="tokyo"))
        assert resp.status_code == 422


# ──────────────────────── INV-002–009: Item fields ────────────────────────


class TestItemFields:
    """INV-002–009: Item fields validation."""

    def test_required_fields(self, client):
        """Empty body should return 422."""
        resp = client.post("/api/inventory/items", json={})
        assert resp.status_code == 422

    def test_client_name_and_sku_and_name(self, client):
        """INV-002, INV-003, INV-004: client_name, sku, name are stored."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(
            client_name="Alpha", sku="ABC-999", name="Widget"
        ))
        assert resp.status_code == 201
        data = resp.json()
        assert data["client_name"] == "Alpha"
        assert data["sku"] == "ABC-999"
        assert data["name"] == "Widget"

    def test_category_validation(self, client):
        """INV-005: category must be fashion|electronics|cosmetics."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(category="toys"))
        assert resp.status_code == 422

    def test_unit_of_measure_validation(self, client):
        """INV-006: unit_of_measure must be unit|box|kg."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(unit_of_measure="litre"))
        assert resp.status_code == 422

    def test_reorder_point_decimal(self, client):
        """INV-007: reorder_point supports decimals (REAL)."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(reorder_point=2.5))
        assert resp.status_code == 201
        assert resp.json()["reorder_point"] == 2.5

    def test_reorder_point_zero_allowed(self, client):
        """reorder_point can be 0."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(reorder_point=0))
        assert resp.status_code == 201

    def test_created_at_and_updated_at_present(self, client):
        """INV-008, INV-009: timestamps are auto-generated."""
        resp = client.post("/api/inventory/items", json=_create_item_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] == data["updated_at"]


# ──────────────────────── INV-010: UNIQUE constraint ────────────────────────


class TestUniqueConstraint:
    """INV-010: (client_name, sku, warehouse) must be unique."""

    def test_duplicate_rejected(self, client):
        payload = _create_item_payload()
        resp1 = client.post("/api/inventory/items", json=payload)
        assert resp1.status_code == 201

        resp2 = client.post("/api/inventory/items", json=payload)
        assert resp2.status_code == 422
        assert "already exists" in resp2.json()["detail"]

    def test_same_sku_different_warehouse_allowed(self, client):
        """Same client+sku in different warehouse is allowed."""
        resp1 = client.post("/api/inventory/items", json=_create_item_payload(warehouse="los_angeles"))
        assert resp1.status_code == 201

        resp2 = client.post("/api/inventory/items", json=_create_item_payload(warehouse="zaragoza"))
        assert resp2.status_code == 201
        assert resp2.json()["warehouse"] == "zaragoza"


# ──────────────────────── INV-011: Multi-warehouse identity ────────────────────────


class TestMultiWarehouseIdentity:
    """INV-011: Same SKU across warehouses are distinct items."""

    def test_distinct_items_per_warehouse(self, client):
        """Same SKU in LA and ZG create separate records."""
        la = client.post("/api/inventory/items", json=_create_item_payload(
            warehouse="los_angeles", sku="SAME-SKU"
        ))
        zg = client.post("/api/inventory/items", json=_create_item_payload(
            warehouse="zaragoza", sku="SAME-SKU"
        ))
        assert la.status_code == 201
        assert zg.status_code == 201
        assert la.json()["id"] != zg.json()["id"]


# ──────────────────────── INV-012–015: Lot fields ────────────────────────


class TestLotFields:
    """INV-012–015: Lot creation and validation."""

    def test_create_lot_for_existing_item(self, client):
        """INV-012, INV-013, INV-014, INV-015: create and verify lot fields."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        lot_resp = client.post(
            f"/api/inventory/items/{item['id']}/lots",
            json={"lot_code": "LOT-001", "expiry_date": "2027-12-31", "received_at": "2026-10-01"},
        )
        assert lot_resp.status_code == 201
        data = lot_resp.json()
        assert data["item_id"] == item["id"]
        assert data["lot_code"] == "LOT-001"
        assert data["expiry_date"] == "2027-12-31"
        assert data["received_at"] == "2026-10-01"
        assert "id" in data

    def test_lot_for_nonexistent_item(self, client):
        """INV-018: Lot creation for non-existent item returns 422."""
        resp = client.post(
            "/api/inventory/items/00000000-0000-0000-0000-000000000000/lots",
            json={"lot_code": "LOT-999", "expiry_date": "2027-12-31", "received_at": "2026-10-01"},
        )
        assert resp.status_code == 422

    def test_list_lots(self, client):
        """List lots for an item."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        lot1 = client.post(
            f"/api/inventory/items/{item['id']}/lots",
            json={"lot_code": "LOT-A", "expiry_date": "2027-06-01", "received_at": "2026-10-01"},
        ).json()
        lot2 = client.post(
            f"/api/inventory/items/{item['id']}/lots",
            json={"lot_code": "LOT-B", "expiry_date": "2027-07-01", "received_at": "2026-10-02"},
        ).json()

        resp = client.get(f"/api/inventory/items/{item['id']}/lots")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] in (lot1["id"], lot2["id"])


# ──────────────────────── INV-016–017: Cosmetics initial_lot ────────────────────────


class TestCosmeticsInitialLot:
    """INV-016: Cosmetics requires initial_lot; INV-017: Fashion/electronics does not."""

    def test_cosmetics_without_initial_lot_rejected(self, client):
        """INV-016: POST cosmetics without initial_lot → 422."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(
            category="cosmetics",
        ))
        assert resp.status_code == 422
        assert "initial_lot" in resp.json()["detail"].lower()

    def test_cosmetics_with_initial_lot_created(self, client):
        """INV-016: POST cosmetics with initial_lot → 201 and lot created."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(
            category="cosmetics",
            initial_lot={"lot_code": "LOT-COS-001", "expiry_date": "2027-12-31", "received_at": "2026-10-01"},
        ))
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        lots_resp = client.get(f"/api/inventory/items/{item_id}/lots")
        assert len(lots_resp.json()) == 1
        assert lots_resp.json()[0]["lot_code"] == "LOT-COS-001"

    def test_fashion_without_initial_lot_created(self, client):
        """INV-017: POST fashion without initial_lot → 201."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(category="fashion"))
        assert resp.status_code == 201

    def test_electronics_without_initial_lot_created(self, client):
        """INV-017: POST electronics without initial_lot → 201."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(category="electronics"))
        assert resp.status_code == 201

    def test_cosmetics_invalid_initial_lot(self, client):
        """POST cosmetics with empty fields in initial_lot → 422."""
        resp = client.post("/api/inventory/items", json=_create_item_payload(
            category="cosmetics",
            initial_lot={"lot_code": "", "expiry_date": "", "received_at": ""},
        ))
        assert resp.status_code == 422


# ──────────────────────── INV-025–033: Stock calculation ────────────────────────


class TestStockCalculation:
    """INV-025–033: Stock derived from movements, never stored."""

    def test_no_stock_column_in_items(self, client):
        """INV-025: No stock column exists in items table. INV-026: Not editable."""
        conn = get_inventory_connection()
        cols = [row[1] for row in conn.execute("PRAGMA table_info(items)").fetchall()]
        assert "stock" not in cols, "stock column must NOT exist in items table"

    def test_new_item_has_zero_stock(self, client):
        """New item returns stock=0."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["stock"] == 0.0

    def test_inbound_increases_stock(self, client):
        """INV-027, INV-031: Inbound adds to stock."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 100.0},
        )
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["stock"] == 100.0

    def test_outbound_decreases_stock(self, client):
        """INV-028, INV-032: Outbound subtracts from stock."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 50.0},
        )
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "outbound", "quantity": 30.0},
        )
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["stock"] == 20.0

    def test_adjustment_signed_positive(self, client):
        """INV-029, INV-033: Positive adjustment increases stock."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "adjustment", "quantity": 15.0, "reason": "count_correction"},
        )
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["stock"] == 15.0

    def test_adjustment_signed_negative(self, client):
        """INV-033: Negative adjustment decreases stock."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 100.0},
        )
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "adjustment", "quantity": -10.0, "reason": "damaged_return"},
        )
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["stock"] == 90.0

    def test_stock_formula_full(self, client):
        """INV-030: stock = inbound - outbound + adjustment."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        client.post(f"/api/inventory/items/{item['id']}/movements", json={"movement_type": "inbound", "quantity": 200.0})
        client.post(f"/api/inventory/items/{item['id']}/movements", json={"movement_type": "outbound", "quantity": 50.0})
        client.post(f"/api/inventory/items/{item['id']}/movements", json={"movement_type": "adjustment", "quantity": 10.0, "reason": "correction"})
        client.post(f"/api/inventory/items/{item['id']}/movements", json={"movement_type": "inbound", "quantity": 30.0})
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["stock"] == 190.0

    def test_stock_decimal_precision(self, client):
        """Stock calculations support decimals."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 10.5},
        )
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "outbound", "quantity": 3.25},
        )
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["stock"] == 7.25

    def test_is_low_stock_function(self, client):
        """is_low_stock returns True when stock <= reorder_point."""
        item = client.post("/api/inventory/items", json=_create_item_payload(reorder_point=5.0)).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 3.0},
        )
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["stock"] == 3.0
        assert detail["is_low_stock"] is True

    def test_not_low_stock(self, client):
        """When stock > reorder_point, is_low_stock is False."""
        item = client.post("/api/inventory/items", json=_create_item_payload(reorder_point=5.0)).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 100.0},
        )
        detail = client.get(f"/api/inventory/items/{item['id']}").json()
        assert detail["is_low_stock"] is False

    def test_get_stock_direct_function(self, db):
        """Direct get_stock() function returns correct float."""
        item_id = "test-item-001"
        db.execute(
            """INSERT INTO items (id, warehouse, client_name, sku, name, category,
                                  unit_of_measure, reorder_point, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item_id, "los_angeles", "Direct", "DIR-001", "Direct Test", "fashion", "unit", 5.0, "2026-10-01", "2026-10-01"),
        )
        db.execute(
            """INSERT INTO stock_movements (id, item_id, movement_type, quantity, reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("mov-001", item_id, "inbound", 25.0, None, "2026-10-01"),
        )
        db.execute(
            """INSERT INTO stock_movements (id, item_id, movement_type, quantity, reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("mov-002", item_id, "outbound", 5.0, None, "2026-10-02"),
        )
        db.commit()

        stock = get_stock(db, item_id)
        assert stock == 20.0

    def test_get_items_with_stock(self, db):
        """get_items_with_stock returns items with calculated stock."""
        item_id = "test-item-002"
        db.execute(
            """INSERT INTO items (id, warehouse, client_name, sku, name, category,
                                  unit_of_measure, reorder_point, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item_id, "los_angeles", "Batch", "BAT-001", "Batch Test", "electronics", "unit", 3.0, "2026-10-01", "2026-10-01"),
        )
        db.execute(
            """INSERT INTO stock_movements (id, item_id, movement_type, quantity, reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("mov-003", item_id, "inbound", 8.0, None, "2026-10-01"),
        )
        db.commit()

        items = get_items_with_stock(db)
        assert len(items) >= 1
        found = [i for i in items if i["id"] == item_id]
        assert len(found) == 1
        assert found[0]["stock"] == 8.0
        assert found[0]["is_low_stock"] is False  # 8 > 3


# ──────────────────────── INV-041: Low-stock endpoint ────────────────────────


class TestLowStockEndpoint:
    """INV-041: Low-stock endpoint returns items with stock <= reorder_point."""

    def test_low_stock_returns_at_risk_items(self, client):
        """GET /api/inventory/low-stock returns grouped items."""
        item = client.post("/api/inventory/items", json=_create_item_payload(
            warehouse="los_angeles", client_name="LowCo", sku="LOW-001", reorder_point=10.0
        )).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 5.0},
        )

        resp = client.get("/api/inventory/low-stock")
        assert resp.status_code == 200
        data = resp.json()
        all_low = data.get("los_angeles", []) + data.get("zaragoza", [])
        assert len(all_low) >= 1
        skus = [i["sku"] for i in all_low]
        assert "LOW-001" in skus

    def test_low_stock_returns_empty_with_healthy_stock(self, client):
        """When no items are low, response has empty lists."""
        item = client.post("/api/inventory/items", json=_create_item_payload(
            reorder_point=5.0
        )).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 100.0},
        )
        resp = client.get("/api/inventory/low-stock")
        data = resp.json()
        assert data["los_angeles"] == []
        assert data["zaragoza"] == []

    def test_low_stock_grouped_by_warehouse(self, client):
        """Items are grouped by warehouse in response."""
        la = client.post("/api/inventory/items", json=_create_item_payload(
            warehouse="los_angeles", client_name="G1", sku="G1-LA", reorder_point=10.0
        )).json()
        zg = client.post("/api/inventory/items", json=_create_item_payload(
            warehouse="zaragoza", client_name="G1", sku="G1-ZG", reorder_point=10.0
        )).json()
        client.post(f"/api/inventory/items/{la['id']}/movements", json={"movement_type": "inbound", "quantity": 3.0})
        client.post(f"/api/inventory/items/{zg['id']}/movements", json={"movement_type": "inbound", "quantity": 2.0})

        resp = client.get("/api/inventory/low-stock")
        data = resp.json()
        assert len(data["los_angeles"]) >= 1
        assert len(data["zaragoza"]) >= 1


# ──────────────────────── INV-042–046: Item CRUD invariants ────────────────────────


class TestItemCrudInvariants:
    """INV-042–046: Create, update, delete invariants."""

    def test_create_rejects_stock_field(self, client):
        """INV-042: Stock is not accepted in creation payload (no stock field in schema)."""
        payload = _create_item_payload()
        assert "stock" not in payload
        resp = client.post("/api/inventory/items", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "stock" not in data  # ItemResponse doesn't include stock

    def test_update_blocks_warehouse_change_with_movements(self, client):
        """INV-043: PUT with different warehouse is rejected if item has movements."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 10.0},
        )
        resp = client.put(
            f"/api/inventory/items/{item['id']}",
            json={"warehouse": "zaragoza"},
        )
        assert resp.status_code == 422
        assert "movement history" in resp.json()["detail"].lower()

    def test_update_allows_warehouse_change_without_movements(self, client):
        """PUT with different warehouse is allowed if item has no movements."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        resp = client.put(
            f"/api/inventory/items/{item['id']}",
            json={"warehouse": "zaragoza"},
        )
        assert resp.status_code == 200
        assert resp.json()["warehouse"] == "zaragoza"

    def test_list_returns_stock(self, client):
        """INV-044: List endpoint returns calculated stock."""
        item = client.post("/api/inventory/items", json=_create_item_payload(sku="LIST-001")).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 42.0},
        )
        resp = client.get("/api/inventory/items")
        assert resp.status_code == 200
        data = resp.json()
        found = [i for i in data if i["sku"] == "LIST-001"]
        assert len(found) == 1
        assert found[0]["stock"] == 42.0
        assert "is_low_stock" in found[0]

    def test_list_filter_by_warehouse(self, client):
        """List endpoint filters by warehouse."""
        client.post("/api/inventory/items", json=_create_item_payload(warehouse="los_angeles", sku="LA-FILTER"))
        client.post("/api/inventory/items", json=_create_item_payload(warehouse="zaragoza", sku="ZG-FILTER"))

        la_resp = client.get("/api/inventory/items?warehouse=los_angeles")
        zg_resp = client.get("/api/inventory/items?warehouse=zaragoza")
        assert la_resp.status_code == 200
        assert zg_resp.status_code == 200
        la_skus = [i["sku"] for i in la_resp.json()]
        zg_skus = [i["sku"] for i in zg_resp.json()]
        assert "LA-FILTER" in la_skus
        assert "ZG-FILTER" in zg_skus
        assert "LA-FILTER" not in zg_skus

    def test_delete_with_movements_rejected(self, client):
        """INV-045: DELETE is rejected if item has movements."""
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 10.0},
        )
        resp = client.delete(f"/api/inventory/items/{item['id']}")
        assert resp.status_code == 422
        assert "movement history" in resp.json()["detail"].lower()

    def test_delete_without_movements(self, client):
        """INV-046: DELETE without movements removes item and associated lots."""
        item = client.post("/api/inventory/items", json=_create_item_payload(
            category="cosmetics",
            initial_lot={"lot_code": "DEL-LOT", "expiry_date": "2027-12-31", "received_at": "2026-10-01"},
        )).json()
        item_id = item["id"]

        detail = client.get(f"/api/inventory/items/{item_id}")
        assert detail.status_code == 200
        assert len(detail.json()["lots"]) == 1

        resp = client.delete(f"/api/inventory/items/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        get_resp = client.get(f"/api/inventory/items/{item_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_item(self, client):
        """DELETE on non-existent item returns 404."""
        resp = client.delete("/api/inventory/items/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ──────────────────────── Expired lots endpoint ────────────────────────


class TestExpiredLots:
    """Expired lots endpoint."""

    def test_expired_lots_returns_list(self, client):
        """GET /api/inventory/lots/expired returns empty list (no seed data in test)."""
        resp = client.get("/api/inventory/lots/expired")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ──────────────────────── List movements endpoint ────────────────────────


class TestListMovements:
    """List movements for an item."""

    def test_list_movements(self, client):
        item = client.post("/api/inventory/items", json=_create_item_payload()).json()
        mov1 = client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "inbound", "quantity": 10.0},
        ).json()
        mov2 = client.post(
            f"/api/inventory/items/{item['id']}/movements",
            json={"movement_type": "outbound", "quantity": 3.0},
        ).json()

        resp = client.get(f"/api/inventory/items/{item['id']}/movements")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] in (mov1["id"], mov2["id"])

    def test_list_movements_nonexistent_item(self, client):
        resp = client.get("/api/inventory/items/00000000-0000-0000-0000-000000000000/movements")
        assert resp.status_code == 404


# ──────────────────────── Health check ────────────────────────


class TestHealth:
    """Health endpoint still works with inventory module loaded."""

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}