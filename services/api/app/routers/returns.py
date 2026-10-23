from fastapi import APIRouter, HTTPException, status

from app.schemas.returns import (
    ReturnRequestInput,
    ReturnRequestSummary,
    ReturnRequestDetail,
    ReturnApproval,
    ReturnInspectionResult,
)

router = APIRouter(prefix="/returns", tags=["returns"])


@router.get("/", response_model=list[ReturnRequestSummary])
def list_return_requests():
    """Listado de solicitudes de devolución."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{return_id}", response_model=ReturnRequestDetail)
def get_return_request(return_id: int):
    """Detalle de una solicitud de devolución."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/", response_model=ReturnRequestDetail, status_code=status.HTTP_201_CREATED)
def create_return_request(body: ReturnRequestInput):
    """Crear solicitud de devolución."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/{return_id}/approve", response_model=ReturnRequestDetail)
def approve_return(return_id: int, body: ReturnApproval):
    """Aprobar o rechazar una devolución."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/{return_id}/inspect", response_model=ReturnRequestDetail)
def inspect_return(return_id: int, body: ReturnInspectionResult):
    """Registrar resultado de inspección de producto devuelto."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")