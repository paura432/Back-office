"""
Tests de integración de endpoints.
Verifica que cada endpoint responda con el código y schema esperados.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("INVENTORY_DEMO_ENABLED", "true")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Health ─────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    async def test_health_endpoint(self, client):
        async with client as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"status": "ok"}


# ── Auth ───────────────────────────────────────────────────────────────

class TestAuthEndpoints:
    async def test_register_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/auth/register", json={
                "email": "test@example.com",
                "password": "SecurePass1",
                "full_name": "Test User",
            })
        assert resp.status_code == 501

    async def test_login_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/auth/login", json={
                "email": "test@example.com",
                "password": "password",
            })
        assert resp.status_code == 501

    async def test_me_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/auth/me")
        assert resp.status_code == 501

    async def test_password_recovery_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/auth/password-recovery", json={
                "email": "test@example.com",
            })
        assert resp.status_code == 501

    async def test_password_reset_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/auth/password-reset", json={
                "token": "abc",
                "new_password": "NewPass123",
            })
        assert resp.status_code == 501


# ── Inventory ──────────────────────────────────────────────────────────

class TestInventoryEndpoints:
    async def test_list_inventory_returns_schema_compliant_records(self, client, monkeypatch):
        from app.routers import inventory

        monkeypatch.setattr(
            inventory,
            "list_inventory",
            lambda **_filters: [{
                "sku": "DEMO-BOX-001",
                "name": "Shipping box",
                "warehouse": "los-angeles",
                "quantity": 38,
                "low_stock_threshold": 10,
            }],
        )
        async with client as ac:
            resp = await ac.get("/inventory/items")
        assert resp.status_code == 200
        assert resp.json()[0]["quantity"] == 38

    async def test_get_inventory_item_returns_404_for_unknown_item(self, client, monkeypatch):
        from app.routers import inventory

        monkeypatch.setattr(inventory, "get_inventory_item", lambda *_args, **_kwargs: None)
        async with client as ac:
            resp = await ac.get("/inventory/items/SKU-001")
        assert resp.status_code == 404

    async def test_get_alerts_returns_schema_compliant_records(self, client, monkeypatch):
        from app.routers import inventory

        monkeypatch.setattr(
            inventory,
            "list_inventory_alerts",
            lambda **_filters: [{
                "sku": "DEMO-TAPE-001",
                "name": "Packing tape",
                "warehouse": "zaragoza",
                "current_quantity": 5,
                "threshold": 12,
            }],
        )
        async with client as ac:
            resp = await ac.get("/inventory/alerts")
        assert resp.status_code == 200
        assert resp.json()[0]["current_quantity"] == 5

    async def test_register_inventory_movement_uses_ledger_service(self, client, monkeypatch):
        from app.routers import inventory

        monkeypatch.setattr(
            inventory,
            "register_inventory_movement",
            lambda movement: {
                "sku": movement.sku,
                "name": "Shipping box",
                "description": "Synthetic example",
                "warehouse": movement.warehouse,
                "quantity": 40,
                "low_stock_threshold": 10,
                "last_updated": None,
            },
        )
        async with client as ac:
            resp = await ac.post("/inventory/movements", json={
                "sku": "DEMO-BOX-001", "warehouse": "los-angeles", "quantity_delta": 2,
            })
        assert resp.status_code == 201
        assert resp.json()["quantity"] == 40


# ── Orders ─────────────────────────────────────────────────────────────

class TestOrdersEndpoints:
    async def test_list_orders_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/orders/")
        assert resp.status_code == 501

    async def test_get_order_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/orders/1")
        assert resp.status_code == 501

    async def test_create_order_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/orders/", json={
                "client_id": 1,
                "items": [{"sku": "SKU-001", "quantity": 1}],
                "shipping_address": "123 Main St",
            })
        assert resp.status_code == 501

    async def test_update_order_status_returns_501(self, client):
        async with client as ac:
            resp = await ac.patch("/orders/1/status", json={"status": "shipped"})
        assert resp.status_code == 501


# ── Shipments ──────────────────────────────────────────────────────────

class TestShipmentsEndpoints:
    async def test_list_shipments_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/shipments/")
        assert resp.status_code == 501

    async def test_get_shipment_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/shipments/1")
        assert resp.status_code == 501

    async def test_track_shipment_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/shipments/tracking/1Z999AA1")
        assert resp.status_code == 501

    async def test_carrier_recommendation_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/shipments/carrier-recommendation", json={
                "destination": "Madrid",
                "weight_kg": 5.0,
            })
        assert resp.status_code == 501


# ── Returns ────────────────────────────────────────────────────────────

class TestReturnsEndpoints:
    async def test_list_returns_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/returns/")
        assert resp.status_code == 501

    async def test_get_return_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/returns/1")
        assert resp.status_code == 501

    async def test_create_return_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/returns/", json={
                "order_id": 1,
                "sku": "SKU-001",
                "quantity": 1,
                "reason": "Damaged",
            })
        assert resp.status_code == 501

    async def test_approve_return_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/returns/1/approve", json={"approved": True})
        assert resp.status_code == 501

    async def test_inspect_return_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/returns/1/inspect", json={
                "condition": "good",
            })
        assert resp.status_code == 501


# ── Customers ──────────────────────────────────────────────────────────

class TestCustomersEndpoints:
    async def test_list_customers_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/customers/")
        assert resp.status_code == 501

    async def test_get_customer_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/customers/1")
        assert resp.status_code == 501

    async def test_get_customer_health_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/customers/1/health")
        assert resp.status_code == 501


# ── Users ──────────────────────────────────────────────────────────────

class TestUsersEndpoints:
    async def test_list_users_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/users/")
        assert resp.status_code == 501

    async def test_get_user_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/users/1")
        assert resp.status_code == 501

    async def test_create_user_returns_501(self, client):
        async with client as ac:
            resp = await ac.post("/users/", json={
                "email": "a@b.com",
                "password": "Secure12",
                "full_name": "A",
                "role": "operator",
            })
        assert resp.status_code == 501

    async def test_update_user_returns_501(self, client):
        async with client as ac:
            resp = await ac.patch("/users/1", json={"full_name": "B"})
        assert resp.status_code == 501


# ── Dashboard ──────────────────────────────────────────────────────────

class TestDashboardEndpoints:
    async def test_executive_dashboard_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/dashboard/executive")
        assert resp.status_code == 501

    async def test_weekly_report_returns_501(self, client):
        async with client as ac:
            resp = await ac.get("/dashboard/weekly-report")
        assert resp.status_code == 501