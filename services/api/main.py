from fastapi import FastAPI

from app.routers import health, auth, inventory, orders, shipments, returns, customers, dashboard, users

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