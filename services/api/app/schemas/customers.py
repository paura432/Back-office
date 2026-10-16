from pydantic import BaseModel, Field
from typing import Optional


class CustomerSummary(BaseModel):
    """Resumen de cliente para listados."""
    id: int
    company_name: str
    contact_email: str
    country: str
    is_active: bool = True


class CustomerDetail(BaseModel):
    """Detalle completo de un cliente."""
    id: int
    company_name: str
    contact_name: str = ""
    contact_email: str
    contact_phone: str = ""
    country: str
    address: str = ""
    is_active: bool = True
    notes: Optional[str] = None


class CustomerHealthScore(BaseModel):
    """Puntuación de salud/riesgo de renovación de un cliente."""
    customer_id: int
    company_name: str
    health_score: float = Field(ge=0, le=100)
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    contract_end_date: Optional[str] = None