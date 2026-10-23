from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserProfileResponse,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    """Registro de nuevo usuario."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """Inicio de sesión. Devuelve token de acceso — nunca expone credenciales."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile():
    """Perfil del usuario autenticado. Sin contraseñas ni secretos."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/password-recovery", response_model=MessageResponse)
def password_recovery(body: PasswordRecoveryRequest):
    """Solicitud de restablecimiento de contraseña."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/password-reset", response_model=MessageResponse)
def password_reset(body: PasswordResetRequest):
    """Restablecimiento de contraseña con token."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")