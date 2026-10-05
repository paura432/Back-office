"""Pydantic schemas for TrackFlow Inventory Manager API."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class WarehouseEnum(str, Enum):
    los_angeles = "los_angeles"
    zaragoza = "zaragoza"


class CategoryEnum(str, Enum):
    fashion = "fashion"
    electronics = "electronics"
    cosmetics = "cosmetics"


class UnitOfMeasureEnum(str, Enum):
    unit = "unit"
    box = "box"
    kg = "kg"


class MovementTypeEnum(str, Enum):
    inbound = "inbound"
    outbound = "outbound"
    adjustment = "adjustment"


# ──────────────────────── Request schemas ────────────────────────


class InitialLotPayload(BaseModel):
    """Lote inicial que se puede crear junto con el artículo.

    Obligatorio cuando category = cosmetics.
    No persiste como campo del Item — solo es parte del contrato de creación.
    """
    lot_code: str = Field(..., min_length=1)
    expiry_date: str = Field(..., min_length=1)
    received_at: str = Field(..., min_length=1)


class ItemCreate(BaseModel):
    warehouse: WarehouseEnum
    client_name: str = Field(..., min_length=1)
    sku: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    category: CategoryEnum
    unit_of_measure: UnitOfMeasureEnum
    reorder_point: float = Field(default=0.0, ge=0)
    initial_lot: Optional[InitialLotPayload] = None


class ItemUpdate(BaseModel):
    warehouse: Optional[WarehouseEnum] = None
    client_name: Optional[str] = Field(None, min_length=1)
    sku: Optional[str] = Field(None, min_length=1)
    name: Optional[str] = Field(None, min_length=1)
    category: Optional[CategoryEnum] = None
    unit_of_measure: Optional[UnitOfMeasureEnum] = None
    reorder_point: Optional[float] = Field(None, ge=0)


# ──────────────────────── Response schemas ────────────────────────


class ItemResponse(BaseModel):
    id: str
    warehouse: str
    client_name: str
    sku: str
    name: str
    category: str
    unit_of_measure: str
    reorder_point: float
    created_at: str
    updated_at: str


class LotResponse(BaseModel):
    id: str
    item_id: str
    lot_code: str
    expiry_date: str
    received_at: str


class StockMovementResponse(BaseModel):
    id: str
    item_id: str
    lot_id: Optional[str] = None
    movement_type: str
    quantity: float
    reason: Optional[str] = None
    created_at: str


class ItemWithStockResponse(ItemResponse):
    stock: float = 0.0
    is_low_stock: bool = False


class ItemDetailResponse(ItemWithStockResponse):
    lots: list[LotResponse] = []
    movements: list[StockMovementResponse] = []


class LowStockItem(BaseModel):
    warehouse: str
    client_name: str
    sku: str
    name: str
    stock: float
    reorder_point: float


class LowStockResponse(BaseModel):
    los_angeles: list[LowStockItem] = []
    zaragoza: list[LowStockItem] = []


class MovementCreate(BaseModel):
    movement_type: MovementTypeEnum
    quantity: float
    lot_id: Optional[str] = None
    reason: Optional[str] = None


# ──────────────────────── Helpers ────────────────────────


def generate_id() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()