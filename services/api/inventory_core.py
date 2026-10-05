"""
Core stock calculation logic for TrackFlow Inventory Manager.

All stock values are derived exclusively from stock_movements.
No stock column is persisted — stock is always calculated on the fly.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def get_stock(conn: sqlite3.Connection, item_id: str) -> float:
    """Calculate the current stock for a given item from its movement history.

    Formula (INV-030):
        stock = SUM(inbound) - SUM(outbound) + SUM(adjustment)

    - inbound:    quantity is added as-is (positive)
    - outbound:   quantity is subtracted (negated)
    - adjustment: quantity is used with its sign (+/-)

    Returns 0.0 if the item has no movements.
    """
    query = """
        SELECT COALESCE(SUM(
            CASE movement_type
                WHEN 'inbound' THEN quantity
                WHEN 'outbound' THEN -quantity
                WHEN 'adjustment' THEN quantity
            END
        ), 0) AS stock
        FROM stock_movements
        WHERE item_id = ?
    """
    cursor = conn.execute(query, (item_id,))
    row = cursor.fetchone()
    return float(row["stock"])


def is_low_stock(conn: sqlite3.Connection, item_id: str, reorder_point: float) -> bool:
    """Return True if the item's current stock is at or below its reorder point.

    INV-041: stock ≤ reorder_point triggers a low-stock signal.
    """
    stock = get_stock(conn, item_id)
    return stock <= reorder_point


def get_items_with_stock(
    conn: sqlite3.Connection,
    warehouse: str | None = None,
) -> list[dict[str, Any]]:
    """Return all items with their calculated stock and low-stock status.

    Each item dict contains all persisted item fields plus:
        - stock:       float — derived from stock_movements
        - is_low_stock: bool  — True when stock ≤ reorder_point

    If warehouse is provided, only items in that warehouse are returned.
    """
    if warehouse:
        cursor = conn.execute(
            "SELECT * FROM items WHERE warehouse = ? ORDER BY client_name, sku",
            (warehouse,),
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM items ORDER BY client_name, sku"
        )

    items: list[dict[str, Any]] = []
    for row in cursor.fetchall():
        item = dict(row)
        stock = get_stock(conn, item["id"])
        item["stock"] = stock
        item["is_low_stock"] = stock <= item["reorder_point"]
        items.append(item)

    return items