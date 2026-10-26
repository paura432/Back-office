from collections.abc import Iterable

import pytest

import seed_inventory


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.last_query = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        self.last_query = query
        self.connection.executed.append((query, params))

    def executemany(self, query, params_seq: Iterable[tuple]):
        rows = list(params_seq)
        self.connection.many.append((query, rows))

    def fetchone(self):
        return (1,) if self.connection.has_untagged_movements and "seed_key IS NULL" in self.last_query else None


class FakeConnection:
    def __init__(self, has_untagged_movements=False):
        self.has_untagged_movements = has_untagged_movements
        self.executed = []
        self.many = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def cursor(self):
        return FakeCursor(self)


def test_seed_uses_cursor_executemany_and_stable_seed_keys_without_deletes(monkeypatch, capsys):
    connections = []

    def connect(_dsn):
        connection = FakeConnection()
        connections.append(connection)
        return connection

    monkeypatch.setattr(seed_inventory, "DATABASE_DSN", "postgresql://u:p@localhost/trackflow")
    monkeypatch.setattr(seed_inventory.psycopg, "connect", connect)

    seed_inventory.main()
    seed_inventory.main()

    assert len(connections) == 2
    for connection in connections:
        sql = "\n".join(query for query, _ in connection.executed)
        sql += "\n" + "\n".join(query for query, _ in connection.many)
        assert "DELETE" not in sql.upper()
        assert len(connection.many) == 2
        movement_query, movement_rows = connection.many[1]
        assert "ON CONFLICT (seed_key)" in movement_query
        assert movement_rows
        assert all(row[0].startswith("inventory-demo-v1:") for row in movement_rows)

    # A rerun has precisely the same seed identities and deltas to UPSERT.
    assert connections[0].many[1][1] == connections[1].many[1][1]
    assert "Seeded 12" in capsys.readouterr().out


def test_seed_refuses_ambiguous_untagged_movements(monkeypatch):
    connection = FakeConnection(has_untagged_movements=True)
    monkeypatch.setattr(seed_inventory, "DATABASE_DSN", "postgresql://u:p@localhost/trackflow")
    monkeypatch.setattr(seed_inventory.psycopg, "connect", lambda _dsn: connection)

    with pytest.raises(RuntimeError, match="origin is ambiguous"):
        seed_inventory.main()

    assert len(connection.many) == 1  # Only item metadata; no movements were changed.
    assert not any("DELETE" in query.upper() for query, _ in connection.executed)
