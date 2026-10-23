from fastapi import APIRouter, HTTPException, status

from app.schemas.dashboard import ExecutiveDashboard, WeeklyReport

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/executive", response_model=ExecutiveDashboard)
def get_executive_dashboard():
    """Dashboard ejecutivo global con KPIs en tiempo real."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/weekly-report", response_model=WeeklyReport)
def get_weekly_report():
    """Informe semanal generado automáticamente."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")