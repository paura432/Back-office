from fastapi import FastAPI

from db import check_database
from app.routers import health, auth, inventory, orders, shipments, returns, customers, dashboard, users
from app.schemas.status import StatusResponse

app = FastAPI(title="TrackFlow API", version="0.1.0")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(shipments.router)
app.include_router(returns.router)
app.include_router(customers.router)
app.include_router(dashboard.router)
app.include_router(users.router)


@app.get(
    "/status",
    response_model=StatusResponse,
    tags=["health"],
)
def status() -> StatusResponse:
    """Operational status of the API and its PostgreSQL connection.

    Returns ``{"status": "operational"}`` only when a live ``SELECT 1``
    against PostgreSQL succeeds; otherwise returns ``degraded``. Credentials
    are never part of the response.
    """
    if check_database():
        return StatusResponse(status="operational")
    return StatusResponse(status="degraded")
