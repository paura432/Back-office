from typing import Literal

from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Operational status of the API and its PostgreSQL dependency."""

    status: Literal["operational", "degraded"]
