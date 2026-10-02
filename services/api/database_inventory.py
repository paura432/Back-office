"""
Database module for TrackFlow Inventory Manager.
Uses SQLite via standard library sqlite3. No ORM.
Completely isolated from the Incident Manager database.

DB path is configurable via environment variable INVENTORY_DB_PATH
(default: inventory.db in the services/api directory).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent / "inventory.db"


def get_inventory_db_path() -> str:
    """Return the inventory database path, respecting INVENTORY_DB_PATH env var."""
    return os.environ.get("INVENTORY_DB_PATH", str(DEFAULT_DB_PATH))


def get_inventory_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with row factory and foreign keys enabled."""
    path = db_path or get_inventory_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_inventory_db(conn: sqlite3.Connection | None = None) -> None:
    """Initialize inventory database tables. Idempotent."""
    close = conn is None
    if conn is None:
        conn = get_inventory_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            warehouse TEXT NOT NULL CHECK (warehouse IN ('los_angeles', 'zaragoza')),
            client_name TEXT NOT NULL,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK (category IN ('fashion', 'electronics', 'cosmetics')),
            unit_of_measure TEXT NOT NULL CHECK (unit_of_measure IN ('unit', 'box', 'kg')),
            reorder_point REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (client_name, sku, warehouse)
        );

        CREATE TABLE IF NOT EXISTS lots (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL REFERENCES items(id),
            lot_code TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            received_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stock_movements (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL REFERENCES items(id),
            lot_id TEXT REFERENCES lots(id),
            movement_type TEXT NOT NULL CHECK (movement_type IN ('inbound', 'outbound', 'adjustment')),
            quantity REAL NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inventory_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    if close:
        conn.close()