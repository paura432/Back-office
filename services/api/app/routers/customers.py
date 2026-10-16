from fastapi import APIRouter, HTTPException, status

from app.schemas.customers import CustomerSummary, CustomerDetail, CustomerHealthScore

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/", response_model=list[CustomerSummary])
def list_customers():
    """Listado resumido de clientes."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{customer_id}", response_model=CustomerDetail)
def get_customer(customer_id: int):
    """Detalle completo de un cliente."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{customer_id}/health", response_model=CustomerHealthScore)
def get_customer_health(customer_id: int):
    """Puntuación de salud y riesgo de renovación."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")