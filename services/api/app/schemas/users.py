from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    """Creación de usuario (admin)."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)
    role: str = Field(default="operator", pattern="^(admin|operator|viewer)$")


class UserUpdate(BaseModel):
    """Actualización de usuario — solo campos editables."""
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    role: Optional[str] = Field(default=None, pattern="^(admin|operator|viewer)$")
    is_active: Optional[bool] = None


class UserSummary(BaseModel):
    """Resumen de usuario para listados."""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool


class UserDetail(BaseModel):
    """Detalle completo de usuario — sin contraseñas."""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str