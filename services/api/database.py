"""
Database module for TrackFlow Incident Manager.
Uses SQLite via standard library sqlite3. No ORM.
DB path is configurable via environment variable INCIDENT_DB_PATH (default: incidents.db).
"""

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent / "incidents.db"


def get_db_path() -> str:
    """Return the database path, respecting INCIDENT_DB_PATH env var."""
    return os.environ.get("INCIDENT_DB_PATH", str(DEFAULT_DB_PATH))


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Initialize database tables. Idempotent."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            warehouse_location TEXT,
            client_name TEXT,
            channel TEXT NOT NULL,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            responsible_area TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            assigned_to TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS incident_audit_log (
            id TEXT PRIMARY KEY,
            incident_id TEXT NOT NULL,
            field_changed TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (incident_id) REFERENCES incidents(id)
        );

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    if close:
        conn.close()