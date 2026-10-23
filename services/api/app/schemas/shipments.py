from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TrackingEvent(BaseModel):
    """Evento individual de tracking."""
    timestamp: datetime
    location: str = ""
    status: str
    description: str = ""


class ShipmentSummary(BaseModel):
    """Resumen de envío para listados."""
    id: int
    tracking_number: str
    carrier: str
    recipient: str
    status: str
    estimated_delivery: Optional[str] = None


class ShipmentDetail(BaseModel):
    """Detalle completo de un envío con historial de eventos."""
    id: int
    tracking_number: str
    carrier: str
    carrier_tracking_url: Optional[str] = None
    recipient: str
    destination: str
    weight_kg: float = Field(ge=0)
    status: str
    estimated_delivery: Optional[str] = None
    events: list[TrackingEvent] = []


class CarrierRecommendationRequest(BaseModel):
    """Solicitud de recomendación de transportista."""
    destination: str = Field(..., min_length=1, max_length=200)
    weight_kg: float = Field(gt=0)
    urgency: str = Field(default="normal", pattern="^(low|normal|high)$")


class CarrierRecommendation(BaseModel):
    """Recomendación de transportista."""
    carrier: str
    estimated_cost: float = Field(ge=0)
    estimated_days: int = Field(ge=1)
    confidence_score: float = Field(ge=0, le=1)