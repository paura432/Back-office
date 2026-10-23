from unittest.mock import MagicMock, patch

import psycopg

from db import check_database


def test_check_database_executes_select_one_and_returns_true():
    connection = MagicMock()
    cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)

    with patch("db.psycopg.connect", return_value=connection) as connect:
        assert check_database() is True

    connect.assert_called_once()
    cursor.execute.assert_called_once_with("SELECT 1")
    cursor.fetchone.assert_called_once_with()


def test_check_database_returns_false_without_exposing_connection_error():
    with patch(
        "db.psycopg.connect",
        side_effect=psycopg.OperationalError(
            "postgresql://secret-user:secret-password@db/secret-db"
        ),
    ):
        assert check_database() is False
