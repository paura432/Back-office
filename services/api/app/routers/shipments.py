from fastapi import APIRouter, HTTPException, status

from app.schemas.shipments import (
    ShipmentSummary,
    ShipmentDetail,
    TrackingEvent,
    CarrierRecommendationRequest,
    CarrierRecommendation,
)

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("/", response_model=list[ShipmentSummary])
def list_shipments():
    """Listado resumido de envíos."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{shipment_id}", response_model=ShipmentDetail)
def get_shipment(shipment_id: int):
    """Detalle completo de un envío con tracking."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/tracking/{tracking_number}", response_model=ShipmentDetail)
def track_shipment(tracking_number: str):
    """Tracking unificado por número de seguimiento."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/carrier-recommendation", response_model=list[CarrierRecommendation])
def recommend_carrier(body: CarrierRecommendationRequest):
    """Recomendación de transportista óptimo."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")