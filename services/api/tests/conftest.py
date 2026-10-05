"""Pytest configuration for TrackFlow API tests."""
import os
import sys
import tempfile
from pathlib import Path

# ── Incident Manager DB ──────────────────────────────────────────────────
_inc_fd, _inc_path = tempfile.mkstemp(suffix=".incident.test.db")
os.environ["INCIDENT_DB_PATH"] = _inc_path

# ── Inventory Manager DB ─────────────────────────────────────────────────
_inv_fd, _inv_path = tempfile.mkstemp(suffix=".inventory.test.db")
os.environ["INVENTORY_DB_PATH"] = _inv_path

# Add the api directory to the Python path so imports work
API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def pytest_unconfigure(config):
    """Clean up the temp database files after all tests."""
    os.close(_inc_fd)
    if os.path.exists(_inc_path):
        os.unlink(_inc_path)
    os.close(_inv_fd)
    if os.path.exists(_inv_path):
        os.unlink(_inv_path)