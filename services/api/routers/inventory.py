"""Routers for TrackFlow Inventory Manager — items CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from database_inventory import get_inventory_connection
from inventory_core import get_stock, get_items_with_stock, is_low_stock
from schemas.inventory import (
    ItemCreate,
    ItemDetailResponse,
    ItemResponse,
    ItemUpdate,
    ItemWithStockResponse,
    LotResponse,
    StockMovementResponse,
    generate_id,
    utc_now,
    WarehouseEnum,
    CategoryEnum,
    UnitOfMeasureEnum,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def get_db():
    conn = get_inventory_connection()
    try:
        yield conn
    finally:
        conn.close()


def _row_to_item_response(row: dict) -> dict:
    return {
        "id": row["id"],
        "warehouse": row["warehouse"],
        "client_name": row["client_name"],
        "sku": row["sku"],
        "name": row["name"],
        "category": row["category"],
        "unit_of_measure": row["unit_of_measure"],
        "reorder_point": float(row["reorder_point"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_lot_response(row: dict) -> dict:
    return {
        "id": row["id"],
        "item_id": row["item_id"],
        "lot_code": row["lot_code"],
        "expiry_date": row["expiry_date"],
        "received_at": row["received_at"],
    }


def _row_to_movement_response(row: dict) -> dict:
    return {
        "id": row["id"],
        "item_id": row["item_id"],
        "lot_id": row.get("lot_id"),
        "movement_type": row["movement_type"],
        "quantity": float(row["quantity"]),
        "reason": row.get("reason"),
        "created_at": row["created_at"],
    }


# ──────────────────────── Items CRUD ────────────────────────


@router.get("/items", response_model=list[ItemWithStockResponse])
def list_items(
    warehouse: str | None = Query(None),
    db=Depends(get_db),
):
    """List all items with derived stock and low-stock signal.

    Optional warehouse filter: ?warehouse=los_angeles|zaragoza
    """
    if warehouse is not None and warehouse not in ("los_angeles", "zaragoza"):
        raise HTTPException(status_code=422, detail=f"Invalid warehouse: {warehouse}")

    return get_items_with_stock(db, warehouse=warehouse)


@router.get("/items/{item_id}", response_model=ItemDetailResponse)
def get_item(item_id: str, db=Depends(get_db)):
    """Get item detail with derived stock, lots, and recent movements."""
    row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    item = _row_to_item_response(dict(row))
    stock = get_stock(db, item_id)
    item["stock"] = stock
    item["is_low_stock"] = stock <= item["reorder_point"]

    # Load lots
    lots_rows = db.execute(
        "SELECT * FROM lots WHERE item_id = ? ORDER BY received_at DESC",
        (item_id,),
    ).fetchall()
    item["lots"] = [_row_to_lot_response(dict(r)) for r in lots_rows]

    # Load last 20 movements
    mov_rows = db.execute(
        "SELECT * FROM stock_movements WHERE item_id = ? ORDER BY created_at DESC LIMIT 20",
        (item_id,),
    ).fetchall()
    item["movements"] = [_row_to_movement_response(dict(r)) for r in mov_rows]

    return item


@router.post("/items", response_model=ItemResponse, status_code=201)
def create_item(payload: ItemCreate, db=Depends(get_db)):
    """Create a new inventory item.

    - Validates that warehouse, category, unit_of_measure are from the closed catalog.
    - Rejects duplicate (client_name, sku, warehouse).
    - Never accepts or stores stock directly (INV-042).
    - For cosmetics, use INV-T05 (not implemented here).
    """
    now = utc_now()
    item_id = generate_id()

    # Validate warehouse is from catalog (via Pydantic enum, but explicit check)
    if payload.warehouse.value not in ("los_angeles", "zaragoza"):
        raise HTTPException(status_code=422, detail=f"Invalid warehouse: {payload.warehouse.value}")
    if payload.category.value not in ("fashion", "electronics", "cosmetics"):
        raise HTTPException(status_code=422, detail=f"Invalid category: {payload.category.value}")
    if payload.unit_of_measure.value not in ("unit", "box", "kg"):
        raise HTTPException(status_code=422, detail=f"Invalid unit_of_measure: {payload.unit_of_measure.value}")

    # Check duplicate (client_name, sku, warehouse)
    existing = db.execute(
        "SELECT id FROM items WHERE client_name = ? AND sku = ? AND warehouse = ?",
        (payload.client_name, payload.sku, payload.warehouse.value),
    ).fetchone()
    if existing:
        raise HTTPException(
            status_code=422,
            detail=f"Item with client_name='{payload.client_name}', sku='{payload.sku}', "
                   f"warehouse='{payload.warehouse.value}' already exists",
        )

    db.execute(
        """
        INSERT INTO items (id, warehouse, client_name, sku, name, category,
                           unit_of_measure, reorder_point, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            payload.warehouse.value,
            payload.client_name,
            payload.sku,
            payload.name,
            payload.category.value,
            payload.unit_of_measure.value,
            payload.reorder_point,
            now,
            now,
        ),
    )
    db.commit()

    row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return _row_to_item_response(dict(row))


@router.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: str, payload: ItemUpdate, db=Depends(get_db)):
    """Update an existing item.

    - If the item has movements, warehouse change is rejected (INV-043).
    - Never accepts or stores stock directly.
    """
    row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    current = dict(row)
    now = utc_now()

    # Check if item has movements — if so, warehouse cannot change
    if payload.warehouse is not None and payload.warehouse.value != current["warehouse"]:
        mov_count = db.execute(
            "SELECT COUNT(*) as cnt FROM stock_movements WHERE item_id = ?",
            (item_id,),
        ).fetchone()["cnt"]
        if mov_count > 0:
            raise HTTPException(
                status_code=422,
                detail="Cannot change warehouse: item has movement history",
            )

    updates: list[str] = []
    params: list = []

    UPDATABLE_FIELDS = {
        "warehouse": lambda v: v.value,
        "client_name": lambda v: v,
        "sku": lambda v: v,
        "name": lambda v: v,
        "category": lambda v: v.value,
        "unit_of_measure": lambda v: v.value,
        "reorder_point": lambda v: v,
    }

    for field, converter in UPDATABLE_FIELDS.items():
        if field not in payload.model_fields_set:
            continue
        new_val = converter(getattr(payload, field))
        old_val = current.get(field)
        if old_val == new_val:
            continue
        updates.append(f"{field} = ?")
        params.append(new_val)

    if not updates:
        # No changes — return current item
        return _row_to_item_response(current)

    updates.append("updated_at = ?")
    params.append(now)
    params.append(item_id)

    db.execute(
        f"UPDATE items SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    db.commit()

    updated = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return _row_to_item_response(dict(updated))


@router.delete("/items/{item_id}", status_code=200)
def delete_item(item_id: str, db=Depends(get_db)):
    """Delete an item.

    - If item has movements → reject (INV-045).
    - If no movements → delete item and all associated lots in one transaction (INV-046).
    """
    row = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    # Check if item has movements
    mov_count = db.execute(
        "SELECT COUNT(*) as cnt FROM stock_movements WHERE item_id = ?",
        (item_id,),
    ).fetchone()["cnt"]
    if mov_count > 0:
        raise HTTPException(
            status_code=422,
            detail="Cannot delete item with movement history",
        )

    # Delete lots first, then item (in transaction)
    db.execute("DELETE FROM lots WHERE item_id = ?", (item_id,))
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()

    return {"deleted": True, "id": item_id}