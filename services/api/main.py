import logging
from time import perf_counter

from fastapi import FastAPI, Request

from db import check_database
from app.routers import health, auth, inventory, orders, shipments, returns, customers, dashboard, users, telemetry
from app.schemas.status import StatusResponse

app = FastAPI(title="TrackFlow API", version="0.1.0")
logger = logging.getLogger("trackflow.http")


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    """Log request duration against the matched route template, not raw URLs."""
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        route_template = getattr(route, "path", "<unmatched>")
        logger.info(
            "http_request method=%s route=%s status_code=%d duration_ms=%.3f",
            request.method,
            route_template,
            status_code,
            (perf_counter() - started_at) * 1000,
        )

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(shipments.router)
app.include_router(returns.router)
app.include_router(customers.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(telemetry.router)


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
