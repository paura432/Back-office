from fastapi import FastAPI

from db import check_database

app = FastAPI(title="TrackFlow API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict[str, str]:
    """Operational status of the API and its PostgreSQL connection.

    Returns ``{"status": "operational"}`` only when a live ``SELECT 1``
    against PostgreSQL succeeds; otherwise returns ``degraded``. Credentials
    are never part of the response.
    """
    if check_database():
        return {"status": "operational"}
    return {"status": "degraded"}