from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class RegisterRequest(BaseModel):
    """Registro de nuevo usuario."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Inicio de sesión."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Respuesta con token de acceso."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserProfileResponse(BaseModel):
    """Perfil público del usuario autenticado — sin contraseñas ni secretos."""
    id: int
    email: str
    full_name: str
    is_active: bool


class PasswordRecoveryRequest(BaseModel):
    """Solicitud de restablecimiento de contraseña."""
    email: EmailStr


class PasswordResetRequest(BaseModel):
    """Restablecimiento de contraseña con token."""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje."""
    message: str