from fastapi import APIRouter, HTTPException, status

from app.schemas.inventory import InventoryItemSummary, InventoryItemDetail, InventoryAlert

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/items", response_model=list[InventoryItemSummary])
def list_inventory():
    """Listado resumido de ítems de inventario."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/items/{sku}", response_model=InventoryItemDetail)
def get_inventory_item(sku: str):
    """Detalle de un ítem de inventario."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/alerts", response_model=list[InventoryAlert])
def get_low_stock_alerts():
    """Alertas de stock bajo."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")