from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class OrderItemInput(BaseModel):
    """Producto dentro de un pedido (entrada)."""
    sku: str
    quantity: int = Field(ge=1)


class OrderCreateRequest(BaseModel):
    """Creación de un nuevo pedido."""
    client_id: int
    items: list[OrderItemInput] = Field(..., min_length=1)
    shipping_address: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = None


class OrderItemSummary(BaseModel):
    """Producto dentro de un pedido (salida)."""
    sku: str
    name: str
    quantity: int = Field(ge=1)


class OrderSummary(BaseModel):
    """Resumen de pedido para listados."""
    id: int
    client_name: str
    status: str
    item_count: int = Field(ge=0)
    created_at: datetime


class OrderDetail(BaseModel):
    """Detalle completo de un pedido."""
    id: int
    client_id: int
    client_name: str
    items: list[OrderItemSummary]
    status: str
    shipping_address: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class OrderStatusUpdate(BaseModel):
    """Actualización de estado de un pedido."""
    status: str = Field(..., min_length=1, max_length=50)