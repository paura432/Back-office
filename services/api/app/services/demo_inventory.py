"""Local PostgreSQL inventory backed by an append-only movement ledger.

This deliberately supports only the repository's local Compose database. It
does not connect to a remote database or represent production inventory.
"""

from __future__ import annotations

from threading import Lock
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from db import DATABASE_DSN
from app.schemas.inventory import (
    InventoryAlert,
    InventoryItemDetail,
    InventoryItemSummary,
    InventoryMovementCreate,
)
from app.services.ttl_cache import TTLCache

INVENTORY_TTL_SECONDS = 30.0
inventory_cache: TTLCache[object] = TTLCache(INVENTORY_TTL_SECONDS)

_LOCAL_DATABASE_HOSTS = {"db", "localhost", "127.0.0.1", "::1"}
_schema_lock = Lock()
_schema_initialized = False


class InventoryItemNotFound(Exception):
    """Raised when a movement references an unknown SKU/warehouse pair."""


class InsufficientInventory(Exception):
    """Raised when a movement would reduce the derived stock below zero."""


def _assert_local_database(dsn: str = DATABASE_DSN) -> None:
    parsed = urlparse(dsn)
    database = parsed.path.lstrip("/")
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or parsed.hostname not in _LOCAL_DATABASE_HOSTS
        or database != "trackflow"
    ):
        raise RuntimeError(
            "Inventory demo is restricted to the local trackflow database"
        )


def _connect() -> psycopg.Connection:
    _assert_local_database()
    return psycopg.connect(DATABASE_DSN, row_factory=dict_row)


def ensure_inventory_schema() -> None:
    """Create the local demo schema once for this API process."""
    global _schema_initialized
    if _schema_initialized:
        return
    with _schema_lock:
        if _schema_initialized:
            return
        with _connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_items (
                    sku text NOT NULL,
                    warehouse text NOT NULL,
                    name text NOT NULL,
                    description text NOT NULL DEFAULT '',
                    low_stock_threshold integer CHECK (low_stock_threshold >= 0),
                    PRIMARY KEY (sku, warehouse)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id bigserial PRIMARY KEY,
                    sku text NOT NULL,
                    warehouse text NOT NULL,
                    quantity_delta integer NOT NULL CHECK (quantity_delta <> 0),
                    occurred_at timestamptz NOT NULL DEFAULT now(),
                    FOREIGN KEY (sku, warehouse)
                        REFERENCES inventory_items (sku, warehouse)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS inventory_movements_item_idx "
                "ON inventory_movements (sku, warehouse, occurred_at DESC)"
            )
        _schema_initialized = True


def _normalize(value: str | None) -> str | None:
    return value.strip().lower() if value and value.strip() else None


def list_inventory(
    warehouse: str | None = None,
    sku: str | None = None,
    q: str | None = None,
) -> list[InventoryItemSummary]:
    normalized_warehouse = _normalize(warehouse)
    normalized_sku = sku.strip().upper() if sku and sku.strip() else None
    normalized_query = _normalize(q)
    key = ("items", normalized_warehouse, normalized_sku, normalized_query)

    def load() -> list[InventoryItemSummary]:
        ensure_inventory_schema()
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT item.sku, item.name, item.warehouse,
                       GREATEST(COALESCE(SUM(movement.quantity_delta), 0), 0)::integer AS quantity,
                       item.low_stock_threshold
                  FROM inventory_items AS item
                  LEFT JOIN inventory_movements AS movement
                    ON movement.sku = item.sku AND movement.warehouse = item.warehouse
                 WHERE (%s::text IS NULL OR item.warehouse = %s)
                   AND (%s::text IS NULL OR item.sku = %s)
                   AND (%s::text IS NULL OR item.name ILIKE %s OR item.sku ILIKE %s)
                 GROUP BY item.sku, item.name, item.warehouse, item.low_stock_threshold
                 ORDER BY item.warehouse, item.sku
                """,
                (
                    normalized_warehouse,
                    normalized_warehouse,
                    normalized_sku,
                    normalized_sku,
                    normalized_query,
                    f"%{normalized_query}%" if normalized_query else None,
                    f"%{normalized_query}%" if normalized_query else None,
                ),
            ).fetchall()
        return [InventoryItemSummary(**row) for row in rows]

    return inventory_cache.get_or_set(key, load)


def list_inventory_alerts(warehouse: str | None = None) -> list[InventoryAlert]:
    normalized_warehouse = _normalize(warehouse)
    key = ("alerts", normalized_warehouse)

    def load() -> list[InventoryAlert]:
        ensure_inventory_schema()
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT item.sku, item.name, item.warehouse,
                       GREATEST(COALESCE(SUM(movement.quantity_delta), 0), 0)::integer AS current_quantity,
                       item.low_stock_threshold AS threshold
                  FROM inventory_items AS item
                  LEFT JOIN inventory_movements AS movement
                    ON movement.sku = item.sku AND movement.warehouse = item.warehouse
                 WHERE item.low_stock_threshold IS NOT NULL
                   AND (%s::text IS NULL OR item.warehouse = %s)
                 GROUP BY item.sku, item.name, item.warehouse, item.low_stock_threshold
                HAVING COALESCE(SUM(movement.quantity_delta), 0) <= item.low_stock_threshold
                 ORDER BY item.warehouse, item.sku
                """,
                (normalized_warehouse, normalized_warehouse),
            ).fetchall()
        return [InventoryAlert(**row) for row in rows]

    return inventory_cache.get_or_set(key, load)


def get_inventory_item(
    sku: str, warehouse: str | None = None
) -> InventoryItemDetail | None:
    normalized_sku = sku.strip().upper()
    normalized_warehouse = _normalize(warehouse)
    key = ("item", normalized_sku, normalized_warehouse)

    def load() -> InventoryItemDetail | None:
        ensure_inventory_schema()
        with _connect() as connection:
            row = connection.execute(
                """
                SELECT item.sku, item.name, item.description, item.warehouse,
                       GREATEST(COALESCE(SUM(movement.quantity_delta), 0), 0)::integer AS quantity,
                       item.low_stock_threshold,
                       MAX(movement.occurred_at) AS last_updated
                  FROM inventory_items AS item
                  LEFT JOIN inventory_movements AS movement
                    ON movement.sku = item.sku AND movement.warehouse = item.warehouse
                 WHERE item.sku = %s AND (%s::text IS NULL OR item.warehouse = %s)
                 GROUP BY item.sku, item.name, item.description, item.warehouse,
                          item.low_stock_threshold
                 ORDER BY item.warehouse
                 LIMIT 1
                """,
                (normalized_sku, normalized_warehouse, normalized_warehouse),
            ).fetchone()
        return InventoryItemDetail(**row) if row else None

    return inventory_cache.get_or_set(key, load)


def register_inventory_movement(
    movement: InventoryMovementCreate,
) -> InventoryItemDetail:
    """Persist a stock delta after preventing a negative derived stock."""
    ensure_inventory_schema()
    sku = movement.sku.strip().upper()
    warehouse = movement.warehouse.strip().lower()
    with _connect() as connection:
        item = connection.execute(
            """SELECT sku, name, description, warehouse, low_stock_threshold
                 FROM inventory_items WHERE sku = %s AND warehouse = %s FOR UPDATE""",
            (sku, warehouse),
        ).fetchone()
        if item is None:
            raise InventoryItemNotFound
        stock = connection.execute(
            """SELECT COALESCE(SUM(quantity_delta), 0)::integer AS quantity
                 FROM inventory_movements WHERE sku = %s AND warehouse = %s""",
            (sku, warehouse),
        ).fetchone()["quantity"]
        if stock + movement.quantity_delta < 0:
            raise InsufficientInventory
        recorded = connection.execute(
            """INSERT INTO inventory_movements (sku, warehouse, quantity_delta)
                 VALUES (%s, %s, %s) RETURNING occurred_at""",
            (sku, warehouse, movement.quantity_delta),
        ).fetchone()
        updated_stock = stock + movement.quantity_delta

    inventory_cache.invalidate()
    return InventoryItemDetail(
        **item,
        quantity=updated_stock,
        last_updated=recorded["occurred_at"],
    )


def reset_inventory_service_for_tests() -> None:
    """Reset process-local setup/cache flags between isolated tests."""
    global _schema_initialized
    _schema_initialized = False
    inventory_cache.invalidate()
