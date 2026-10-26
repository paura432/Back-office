from pydantic import BaseModel, Field, field_validator
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


class InventoryMovementCreate(BaseModel):
    """Signed stock change recorded as an immutable inventory movement."""

    sku: str = Field(min_length=1, max_length=64)
    warehouse: str = Field(min_length=1, max_length=64)
    quantity_delta: int

    @field_validator("quantity_delta")
    @classmethod
    def reject_zero_delta(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_delta must not be zero")
        return value