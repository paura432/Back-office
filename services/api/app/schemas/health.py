from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Respuesta de verificación de estado del servicio."""
    status: str = "ok"