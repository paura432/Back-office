"""Idempotently seed fictional inventory into the local TrackFlow DB only.

Run from services/api with ``uv run python seed_inventory.py``. The target
DSN is validated before any statement; this script refuses remote databases.
"""

from __future__ import annotations

from urllib.parse import urlparse

import psycopg

from db import DATABASE_DSN

LOCAL_HOSTS = {"db", "localhost", "127.0.0.1", "::1"}
ITEMS = (
    ("DEMO-BOX-001", "los-angeles", "Shipping box", "Synthetic corrugated box.", 10, 38),
    ("DEMO-BOX-001", "zaragoza", "Shipping box", "Synthetic corrugated box.", 10, 8),
    ("DEMO-TAPE-001", "los-angeles", "Packing tape", "Synthetic kraft tape roll.", 12, 24),
    ("DEMO-TAPE-001", "zaragoza", "Packing tape", "Synthetic kraft tape roll.", 12, 5),
    ("DEMO-LABEL-001", "los-angeles", "Thermal label", "Synthetic shipping label roll.", 20, 0),
    ("DEMO-LABEL-001", "zaragoza", "Thermal label", "Synthetic shipping label roll.", 20, 67),
    ("DEMO-MAILER-001", "los-angeles", "Recycled mailer", "Synthetic padded mailer.", 15, 14),
    ("DEMO-MAILER-001", "zaragoza", "Recycled mailer", "Synthetic padded mailer.", 15, 31),
    ("DEMO-PALLET-001", "los-angeles", "Reusable pallet", "Synthetic EUR-sized pallet.", 6, 4),
    ("DEMO-PALLET-001", "zaragoza", "Reusable pallet", "Synthetic EUR-sized pallet.", 6, 9),
    ("DEMO-FILL-001", "los-angeles", "Paper filler", "Synthetic recycled paper filler.", 18, 53),
    ("DEMO-FILL-001", "zaragoza", "Paper filler", "Synthetic recycled paper filler.", 18, 17),
)


def validate_local_dsn(dsn: str) -> None:
    parsed = urlparse(dsn)
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or parsed.hostname not in LOCAL_HOSTS
        or parsed.path.lstrip("/") != "trackflow"
    ):
        raise SystemExit("Refusing to seed: DATABASE_DSN must target local database trackflow")


def main() -> None:
    validate_local_dsn(DATABASE_DSN)
    with psycopg.connect(DATABASE_DSN) as connection:
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
            "ALTER TABLE inventory_movements ADD COLUMN IF NOT EXISTS seed_key text"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS inventory_movements_seed_key_idx "
            "ON inventory_movements (seed_key) WHERE seed_key IS NOT NULL"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS inventory_movements_item_idx "
            "ON inventory_movements (sku, warehouse, occurred_at DESC)"
        )
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO inventory_items (sku, warehouse, name, description, low_stock_threshold)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (sku, warehouse) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    low_stock_threshold = EXCLUDED.low_stock_threshold
                """,
                [item[:5] for item in ITEMS],
            )

            # Older demo runs had no provenance key. Never guess which rows are
            # disposable: fail without touching the existing movement ledger.
            cursor.execute(
                """
                SELECT 1
                  FROM inventory_movements
                 WHERE (sku, warehouse) IN (SELECT * FROM unnest(%s::text[], %s::text[]))
                   AND seed_key IS NULL
                 LIMIT 1
                """,
                ([item[0] for item in ITEMS], [item[1] for item in ITEMS]),
            )
            if cursor.fetchone() is not None:
                raise RuntimeError(
                    "Refusing to seed item pairs with untagged movements; "
                    "their origin is ambiguous"
                )

            seed_movements = []
            for sku, warehouse, _name, _description, _threshold, quantity in ITEMS:
                if quantity == 0:
                    continue
                # Two fixed, tagged deltas demonstrate a ledger-derived stock.
                first_delta = max(1, quantity // 3)
                second_delta = quantity - first_delta
                seed_movements.extend(
                    [
                        (f"inventory-demo-v1:{sku}:{warehouse}:1", sku, warehouse, first_delta),
                        (f"inventory-demo-v1:{sku}:{warehouse}:2", sku, warehouse, second_delta),
                    ]
                )
            cursor.executemany(
                """
                INSERT INTO inventory_movements (seed_key, sku, warehouse, quantity_delta)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (seed_key)
                DO UPDATE SET quantity_delta = EXCLUDED.quantity_delta
                """,
                seed_movements,
            )
    print(f"Seeded {len(ITEMS)} synthetic item/warehouse pairs in local trackflow DB")


if __name__ == "__main__":
    main()
