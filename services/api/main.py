"""
TrackFlow Incident Manager — FastAPI application.
"""

from __future__ import annotations

from fastapi import FastAPI
from database import init_db
from routers.incidents import router as incidents_router
from seed import run_seed

app = FastAPI(
    title="TrackFlow Incident Manager",
    version="0.1.0",
    description="Incident management API for TrackFlow logistics operations.",
)


@app.on_event("startup")
def startup():
    init_db()
    run_seed()


app.include_router(incidents_router)


@app.get("/health")
def health():
    return {"status": "ok"}