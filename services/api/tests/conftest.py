"""Pytest configuration for TrackFlow Incident Manager API tests."""
import os
import sys
import tempfile
from pathlib import Path

# Use a temp file database for all tests (so connections can share it)
_db_fd, _db_path = tempfile.mkstemp(suffix=".test.db")
os.environ["INCIDENT_DB_PATH"] = _db_path

# Add the api directory to the Python path so imports work
API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def pytest_unconfigure(config):
    """Clean up the temp database file after all tests."""
    os.close(_db_fd)
    if os.path.exists(_db_path):
        os.unlink(_db_path)