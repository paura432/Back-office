import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from app.services.inventory_demo_gate import inventory_demo_is_enabled


INVENTORY_ROUTES = (
    ("GET", "/inventory/items"),
    ("GET", "/inventory/items/DEMO-BOX-001"),
    ("GET", "/inventory/alerts"),
    ("POST", "/inventory/movements"),
)


@pytest.mark.parametrize("app_env,enabled", [("", ""), ("development", ""), ("test", "false")])
def test_demo_is_disabled_without_explicit_opt_in(app_env, enabled):
    assert not inventory_demo_is_enabled(app_env, enabled)


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_demo_can_be_enabled_only_in_development_or_test(app_env):
    assert inventory_demo_is_enabled(app_env, "true")


@pytest.mark.parametrize("app_env", ["production", "prod", "staging", ""])
def test_demo_is_never_enabled_outside_allowed_environments(app_env):
    assert not inventory_demo_is_enabled(app_env, "true")


@pytest.mark.parametrize("method,path", INVENTORY_ROUTES)
async def test_every_inventory_route_is_closed_by_default(method, path, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("INVENTORY_DEMO_ENABLED", raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.request(
            method,
            path,
            json={"sku": "DEMO-BOX-001", "warehouse": "los-angeles", "quantity_delta": 1}
            if method == "POST"
            else None,
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Inventory demo is not enabled"


@pytest.mark.parametrize("method,path", INVENTORY_ROUTES)
async def test_every_inventory_route_stays_closed_in_production(method, path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INVENTORY_DEMO_ENABLED", "true")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.request(
            method,
            path,
            json={"sku": "DEMO-BOX-001", "warehouse": "los-angeles", "quantity_delta": 1}
            if method == "POST"
            else None,
        )
    assert response.status_code == 404
