from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ReturnRequestInput(BaseModel):
    """Solicitud de devolución (entrada)."""
    order_id: int
    sku: str
    quantity: int = Field(ge=1)
    reason: str = Field(..., min_length=1, max_length=1000)


class ReturnRequestSummary(BaseModel):
    """Resumen de devolución para listados."""
    id: int
    order_id: int
    sku: str
    status: str
    created_at: datetime


class ReturnRequestDetail(BaseModel):
    """Detalle completo de una solicitud de devolución."""
    id: int
    order_id: int
    sku: str
    product_name: str = ""
    quantity: int = Field(ge=1)
    reason: str
    status: str
    inspection_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ReturnApproval(BaseModel):
    """Decisión de aprobación o rechazo de una devolución."""
    approved: bool
    notes: Optional[str] = None


class ReturnInspectionResult(BaseModel):
    """Resultado de inspección de producto devuelto."""
    condition: str = Field(..., pattern="^(mint|good|fair|damaged|destroyed)$")
    notes: Optional[str] = None