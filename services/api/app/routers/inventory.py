from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.inventory import (
    InventoryAlert,
    InventoryItemDetail,
    InventoryItemSummary,
    InventoryMovementCreate,
)
from app.services.demo_inventory import (
    InsufficientInventory,
    InventoryItemNotFound,
    get_inventory_item,
    list_inventory,
    list_inventory_alerts,
    register_inventory_movement,
)
from app.services.inventory_demo_gate import require_inventory_demo_enabled

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(require_inventory_demo_enabled)],
)


@router.get("/items", response_model=list[InventoryItemSummary])
def get_inventory_items(
    warehouse: str | None = Query(default=None, min_length=1, max_length=64),
    sku: str | None = Query(default=None, min_length=1, max_length=64),
    q: str | None = Query(default=None, min_length=1, max_length=100),
):
    """Lista el stock derivado de movimientos, opcionalmente filtrado."""
    return list_inventory(warehouse=warehouse, sku=sku, q=q)


@router.get("/items/{sku}", response_model=InventoryItemDetail)
def get_inventory_item_detail(
    sku: str,
    warehouse: str | None = Query(default=None, min_length=1, max_length=64),
):
    """Detalle de un ítem de inventario."""
    item = get_inventory_item(sku, warehouse=warehouse)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return item


@router.get("/alerts", response_model=list[InventoryAlert])
def get_low_stock_alerts(
    warehouse: str | None = Query(default=None, min_length=1, max_length=64),
):
    """Alertas de stock bajo."""
    return list_inventory_alerts(warehouse=warehouse)


@router.post(
    "/movements",
    response_model=InventoryItemDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_movement(movement: InventoryMovementCreate):
    """Registra una entrada/salida; la cantidad nunca se edita directamente."""
    try:
        return register_inventory_movement(movement)
    except InventoryItemNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        ) from None
    except InsufficientInventory:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movement would reduce stock below zero",
        ) from None