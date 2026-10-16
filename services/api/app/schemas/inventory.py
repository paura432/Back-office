from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class InventoryItemSummary(BaseModel):
    """Resumen de producto para listados de inventario."""
    sku: str
    name: str
    warehouse: str
    quantity: int = Field(ge=0)
    low_stock_threshold: Optional[int] = None


class InventoryItemDetail(BaseModel):
    """Detalle completo de un ítem de inventario."""
    sku: str
    name: str
    description: str = ""
    warehouse: str
    quantity: int = Field(ge=0)
    low_stock_threshold: Optional[int] = None
    last_updated: Optional[datetime] = None


class InventoryAlert(BaseModel):
    """Alerta de stock bajo."""
    sku: str
    name: str
    warehouse: str
    current_quantity: int = Field(ge=0)
    threshold: int = Field(ge=0)