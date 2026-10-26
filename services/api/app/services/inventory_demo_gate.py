"""Runtime gate for synthetic inventory demo routes.

The feature is opt-in and is never available in production, even if the
explicit enable flag is accidentally set there.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, status


TRUE_VALUES = {"1", "true", "yes", "on"}
ALLOWED_ENVIRONMENTS = {"development", "test"}


def inventory_demo_is_enabled(
    app_env: str | None = None, enabled: str | None = None
) -> bool:
    """Return true only for an explicit enable flag in development/test."""
    environment = (app_env if app_env is not None else os.getenv("APP_ENV", "")).strip().lower()
    flag = (enabled if enabled is not None else os.getenv("INVENTORY_DEMO_ENABLED", ""))
    return environment in ALLOWED_ENVIRONMENTS and flag.strip().lower() in TRUE_VALUES


def require_inventory_demo_enabled() -> None:
    """Reject requests unless the local inventory demo was explicitly enabled."""
    if not inventory_demo_is_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory demo is not enabled",
        )
