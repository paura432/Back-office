from pydantic import BaseModel, Field
from typing import Optional


class DashboardKPI(BaseModel):
    """Indicador individual de dashboard."""
    label: str
    value: float
    unit: str = ""
    previous_value: Optional[float] = None
    trend: Optional[str] = Field(default=None, pattern="^(up|down|stable)$")


class ExecutiveDashboard(BaseModel):
    """Dashboard ejecutivo global con KPIs."""
    total_shipments: DashboardKPI
    on_time_rate: DashboardKPI
    operational_cost: DashboardKPI
    return_rate: DashboardKPI
    active_customers: DashboardKPI
    customer_satisfaction: DashboardKPI


class WeeklyReport(BaseModel):
    """Informe semanal generado automáticamente."""
    week: str
    generated_at: str
    summary: str
    highlights: list[str]
    metrics: dict[str, float]