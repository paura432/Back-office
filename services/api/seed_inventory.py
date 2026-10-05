"""Idempotent seed data for TrackFlow Inventory Manager.

Inserts 15+ items across both warehouses, 3+ clients, 3 categories,
cosmetics with lots, expired lots, low-stock items, and all movement types.
Uses the inventory_metadata table to ensure idempotency (INV-T09).
"""

from __future__ import annotations

from database_inventory import get_inventory_connection
from schemas.inventory import generate_id


def run_inventory_seed() -> None:
    """Insert seed data if not already applied (idempotent)."""
    conn = get_inventory_connection()

    # Check if seed already applied
    existing = conn.execute(
        "SELECT value FROM inventory_metadata WHERE key = 'seed_inventory_applied'"
    ).fetchone()
    if existing:
        return  # Already seeded — idempotent

    now = "2026-10-05T12:00:00"
    expired_date = "2025-01-15T00:00:00"

    # ── Items ──────────────────────────────────────────────────────────
    # Clients: ClientAlpha, ClientBeta, ClientGamma, ClientDelta (4 clients)
    # Warehouses: los_angeles, zaragoza
    # Categories: fashion, electronics, cosmetics

    items_data = [
        # (id_short, warehouse, client, sku, name, category, uom, reorder_point)
        ("itm-la-fa-01", "los_angeles", "ClientAlpha",  "TEE-001", "Basic T-Shirt",        "fashion",     "unit",  5.0),
        ("itm-la-fa-02", "los_angeles", "ClientAlpha",  "TEE-002", "Premium T-Shirt",      "fashion",     "unit",  3.0),
        ("itm-la-fa-03", "los_angeles", "ClientBeta",   "JNS-001", "Slim Jeans",           "fashion",     "unit",  2.0),
        ("itm-la-el-01", "los_angeles", "ClientBeta",   "USB-001", "USB-C Cable 2m",       "electronics", "unit", 10.0),
        ("itm-la-el-02", "los_angeles", "ClientBeta",   "BAT-001", "AA Battery Pack",      "electronics", "box",   8.0),
        ("itm-la-el-03", "los_angeles", "ClientGamma",  "MON-001", "Monitor 27 inch",      "electronics", "unit",  2.0),
        ("itm-la-co-01", "los_angeles", "ClientGamma",  "LIP-001", "Lipstick Red 50",      "cosmetics",   "unit",  4.0),
        ("itm-la-co-02", "los_angeles", "ClientGamma",  "FND-001", "Foundation Beige 30",  "cosmetics",   "unit",  3.0),
        ("itm-la-co-03", "los_angeles", "ClientAlpha",  "MSK-001", "Face Mask Collagen",   "cosmetics",   "unit",  6.0),
        ("itm-zg-fa-01", "zaragoza",    "ClientAlpha",  "TEE-001", "Basic T-Shirt",        "fashion",     "unit",  4.0),
        ("itm-zg-fa-02", "zaragoza",    "ClientDelta",  "SCF-001", "Wool Scarf",           "fashion",     "unit",  3.0),
        ("itm-zg-fa-03", "zaragoza",    "ClientDelta",  "GLV-001", "Leather Gloves",       "fashion",     "unit",  2.0),
        ("itm-zg-el-01", "zaragoza",    "ClientAlpha",  "USB-001", "USB-C Cable 2m",       "electronics", "unit",  5.0),
        ("itm-zg-el-02", "zaragoza",    "ClientBeta",   "HDD-001", "External HDD 1TB",     "electronics", "unit",  3.0),
        ("itm-zg-co-01", "zaragoza",    "ClientDelta",  "LIP-002", "Lipstick Pink 50",     "cosmetics",   "unit",  4.0),
        ("itm-zg-co-02", "zaragoza",    "ClientDelta",  "EYE-001", "Eyeliner Waterproof",  "cosmetics",   "unit",  3.0),
        ("itm-zg-co-03", "zaragoza",    "ClientGamma",  "PWD-001", "Powder Translucent",    "cosmetics",   "kg",    2.5),
    ]

    # Pre-generate UUIDs for items
    item_ids = {short: generate_id() for short, *_ in items_data}

    # Insert items
    for short, warehouse, client, sku, name, category, uom, rp in items_data:
        iid = item_ids[short]
        conn.execute(
            """INSERT INTO items (id, warehouse, client_name, sku, name, category,
                                  unit_of_measure, reorder_point, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (iid, warehouse, client, str(sku), name, category, uom, rp, now, now),
        )

    # ── Lots ────────────────────────────────────────────────────────────
    # Cosmetics items need at least one lot each (INV-051: >=3 cosmetics with lot)
    # One lot with past expiry_date (INV-052: >=1 expired lot)

    lots_data = [
        # (item_short, lot_code, expiry_date, received_at)
        ("itm-la-co-01", "LOT-LIP-RED-01",   "2027-06-30",  "2026-09-01T00:00:00"),
        ("itm-la-co-02", "LOT-FND-BG-01",    "2027-03-15",  "2026-08-15T00:00:00"),
        ("itm-la-co-03", "LOT-MSK-COL-01",   "2026-12-31",  "2026-10-01T00:00:00"),
        ("itm-zg-co-01", "LOT-LIP-PNK-01",   "2027-08-20",  "2026-09-20T00:00:00"),
        ("itm-zg-co-02", "LOT-EYE-WP-01",    expired_date,  "2025-01-10T00:00:00"),  # EXPIRED
        ("itm-zg-co-03", "LOT-PWD-TR-01",    "2027-11-01",  "2026-10-02T00:00:00"),
    ]

    lot_ids = {}
    for item_short, lot_code, expiry, received in lots_data:
        lid = generate_id()
        lot_ids[lot_code] = lid
        conn.execute(
            "INSERT INTO lots (id, item_id, lot_code, expiry_date, received_at) VALUES (?, ?, ?, ?, ?)",
            (lid, item_ids[item_short], lot_code, expiry, received),
        )

    # ── Movements ───────────────────────────────────────────────────────
    # Include inbound, outbound, adjustment (INV-054)
    # Include >=1 adjustment with reason=return_restock (INV-055)
    # Create low-stock conditions for >=2 items (INV-053)

    movements_data = [
        # (item_short, movement_type, quantity, lot_code_or_None, reason)
        # -- LA Fashion --
        ("itm-la-fa-01", "inbound",   50.0,  None,           None),
        ("itm-la-fa-01", "outbound",  20.0,  None,           None),  # stock=30 > rp=5
        ("itm-la-fa-02", "inbound",   2.0,   None,           None),  # stock=2 <= rp=3 → LOW STOCK
        ("itm-la-fa-03", "inbound",   1.0,   None,           None),  # stock=1 <= rp=2 → LOW STOCK
        # -- LA Electronics --
        ("itm-la-el-01", "inbound",   100.0, None,           None),
        ("itm-la-el-01", "outbound",  30.0,  None,           None),
        ("itm-la-el-02", "inbound",   20.0,  None,           None),
        ("itm-la-el-03", "inbound",   5.0,   None,           None),
        ("itm-la-el-03", "outbound",  3.0,   None,           None),
        # -- LA Cosmetics (with lot_id) --
        ("itm-la-co-01", "inbound",   100.0, "LOT-LIP-RED-01", None),
        ("itm-la-co-01", "outbound",  30.0,  "LOT-LIP-RED-01", None),
        ("itm-la-co-02", "inbound",   80.0,  "LOT-FND-BG-01",  None),
        ("itm-la-co-03", "inbound",   60.0,  "LOT-MSK-COL-01", None),
        ("itm-la-co-03", "outbound",  10.0,  "LOT-MSK-COL-01", None),
        # -- ZG Fashion --
        ("itm-zg-fa-01", "inbound",   40.0,  None,           None),
        ("itm-zg-fa-01", "outbound",  15.0,  None,           None),
        ("itm-zg-fa-02", "inbound",   25.0,  None,           None),
        ("itm-zg-fa-03", "inbound",   10.0,  None,           None),
        ("itm-zg-fa-03", "outbound",  8.0,   None,           None),
        # -- ZG Electronics --
        ("itm-zg-el-01", "inbound",   60.0,  None,           None),
        ("itm-zg-el-01", "outbound",  10.0,  None,           None),
        ("itm-zg-el-02", "inbound",   15.0,  None,           None),
        ("itm-zg-el-02", "outbound",  5.0,   None,           None),
        # -- ZG Cosmetics (with lot_id) --
        ("itm-zg-co-01", "inbound",   90.0,  "LOT-LIP-PNK-01", None),
        ("itm-zg-co-01", "outbound",  20.0,  "LOT-LIP-PNK-01", None),
        ("itm-zg-co-02", "inbound",   70.0,  "LOT-EYE-WP-01",  None),  # expired lot
        ("itm-zg-co-03", "inbound",   50.0,  "LOT-PWD-TR-01",  None),
        # -- Adjustment / return_restock (INV-055) --
        ("itm-la-fa-01", "adjustment", 5.0,  None,           "return_restock"),
        ("itm-zg-el-01", "adjustment", 3.0,  None,           "return_restock"),
        ("itm-la-co-01", "adjustment", -2.0, "LOT-LIP-RED-01", "damaged_return"),
    ]

    for item_short, mtype, qty, lot_code, reason in movements_data:
        lid = lot_ids.get(lot_code) if lot_code else None
        conn.execute(
            """INSERT INTO stock_movements (id, item_id, lot_id, movement_type, quantity, reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (generate_id(), item_ids[item_short], lid, mtype, qty, reason, now),
        )

    # ── Mark seed as applied ─────────────────────────────────────────
    conn.execute(
        "INSERT INTO inventory_metadata (key, value) VALUES (?, ?)",
        ("seed_inventory_applied", "true"),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    from database_inventory import init_inventory_db
    conn = get_inventory_connection()
    init_inventory_db(conn)
    conn.close()
    run_inventory_seed()
    print("Inventory seed data applied successfully.")