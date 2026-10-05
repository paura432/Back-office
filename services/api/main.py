"""
TrackFlow Incident Manager — FastAPI application.
"""

from __future__ import annotations

from fastapi import FastAPI
from database import init_db
from routers.incidents import router as incidents_router
from seed import run_seed
from database_inventory import init_inventory_db
from seed_inventory import run_inventory_seed
from routers.inventory import router as inventory_router

app = FastAPI(
    title="TrackFlow Incident Manager",
    version="0.1.0",
    description="Incident management API for TrackFlow logistics operations.",
)


@app.on_event("startup")
def startup():
    init_db()
    run_seed()
    init_inventory_db()
    run_inventory_seed()


app.include_router(incidents_router)
app.include_router(inventory_router)


@app.get("/health")
def health():
    return {"status": "ok"}