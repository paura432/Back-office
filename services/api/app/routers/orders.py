from fastapi import APIRouter, HTTPException, status

from app.schemas.orders import (
    OrderCreateRequest,
    OrderSummary,
    OrderDetail,
    OrderStatusUpdate,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=list[OrderSummary])
def list_orders():
    """Listado resumido de pedidos."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(order_id: int):
    """Detalle completo de un pedido."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
def create_order(body: OrderCreateRequest):
    """Creación de un nuevo pedido."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.patch("/{order_id}/status", response_model=OrderDetail)
def update_order_status(order_id: int, body: OrderStatusUpdate):
    """Actualización de estado de un pedido."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")