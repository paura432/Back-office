"""
Model functions for incidents and audit log.
Raw SQL using sqlite3 — no ORM.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def dict_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def rows_as_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict_from_row(r) for r in rows]