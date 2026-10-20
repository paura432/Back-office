"""PostgreSQL connection helper for the TrackFlow API.

Configuration is read from environment variables with safe development
defaults matching docker-compose.yml. No credentials are ever included in
error messages or responses.
"""

import os

import psycopg

DATABASE_DSN = os.environ.get(
    "DATABASE_DSN",
    "postgresql://{user}:{password}@{host}:{port}/{name}".format(
        host=os.environ.get("DATABASE_HOST", "127.0.0.1"),
        port=os.environ.get("DATABASE_PORT", "5432"),
        name=os.environ.get("DATABASE_NAME", "trackflow"),
        user=os.environ.get("DATABASE_USER", "trackflow"),
        password=os.environ.get("DATABASE_PASSWORD", "trackflow_dev"),
    ),
)


def check_database() -> bool:
    """Execute a trivial statement against PostgreSQL.

    Returns True when the connection and a ``SELECT 1`` succeed, False on
    any connection failure. Sensitive details are intentionally not exposed.
    """
    try:
        with psycopg.connect(DATABASE_DSN, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                return row is not None and row[0] == 1
    except psycopg.Error:
        return False