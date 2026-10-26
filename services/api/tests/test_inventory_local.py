from unittest.mock import MagicMock

import pytest

from app.schemas.inventory import InventoryMovementCreate
from app.services import demo_inventory


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://u:p@remote.example/trackflow",
        "postgresql://u:p@localhost/production",
        "https://localhost/trackflow",
    ],
)
def test_inventory_local_guard_rejects_nonlocal_targets(dsn):
    with pytest.raises(RuntimeError, match="local trackflow database"):
        demo_inventory._assert_local_database(dsn)


def test_movement_invalidates_cached_inventory_and_derives_new_stock(monkeypatch):
    movement = InventoryMovementCreate(
        sku="DEMO-BOX-001", warehouse="los-angeles", quantity_delta=2
    )
    demo_inventory.inventory_cache.invalidate()

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            if "SELECT sku, name, description" in query:
                return FakeResult({
                    "sku": "DEMO-BOX-001",
                    "name": "Shipping box",
                    "description": "Synthetic",
                    "warehouse": "los-angeles",
                    "low_stock_threshold": 10,
                })
            if "SELECT COALESCE(SUM(quantity_delta)" in query:
                return FakeResult({"quantity": 38})
            return FakeResult({"occurred_at": None})

    class FakeResult:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    connection = FakeConnection()
    monkeypatch.setattr(demo_inventory, "ensure_inventory_schema", lambda: None)
    monkeypatch.setattr(demo_inventory, "_connect", lambda: connection)
    monkeypatch.setattr(
        demo_inventory.inventory_cache,
        "get_or_set",
        MagicMock(wraps=demo_inventory.inventory_cache.get_or_set),
    )

    result = demo_inventory.register_inventory_movement(movement)

    assert result.quantity == 40
    assert demo_inventory.inventory_cache._entries == {}


def test_unfiltered_reads_type_null_parameters_for_postgresql(monkeypatch):
    """PostgreSQL cannot infer ``%s IS NULL`` when the bound value is None."""
    queries = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            queries.append(query)
            return self

        def fetchall(self):
            return []

        def fetchone(self):
            return None

    demo_inventory.inventory_cache.invalidate()
    monkeypatch.setattr(demo_inventory, "ensure_inventory_schema", lambda: None)
    monkeypatch.setattr(demo_inventory, "_connect", FakeConnection)

    demo_inventory.list_inventory()
    demo_inventory.list_inventory_alerts()
    demo_inventory.get_inventory_item("DEMO-BOX-001")

    assert len(queries) == 3
    for query in queries:
        assert "%s IS NULL" not in query
        assert "%s::text IS NULL" in query
    demo_inventory.inventory_cache.invalidate()
