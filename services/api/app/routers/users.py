from fastapi import APIRouter, HTTPException, status

from app.schemas.users import UserCreate, UserUpdate, UserSummary, UserDetail

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserSummary])
def list_users():
    """Listado resumido de usuarios."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{user_id}", response_model=UserDetail)
def get_user(user_id: int):
    """Detalle de un usuario — sin contraseñas."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate):
    """Crear un nuevo usuario (admin)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.patch("/{user_id}", response_model=UserDetail)
def update_user(user_id: int, body: UserUpdate):
    """Actualizar datos de un usuario."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")