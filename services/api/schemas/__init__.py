"""Pydantic schemas for TrackFlow Incident Manager API."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ChannelEnum(str, Enum):
    carrier_portal_alert = "carrier_portal_alert"
    client_email = "client_email"
    wms_alert = "wms_alert"
    warehouse_call = "warehouse_call"
    dashboard = "dashboard"


class IncidentTypeEnum(str, Enum):
    lost_parcel = "lost_parcel"
    inventory_discrepancy = "inventory_discrepancy"
    carrier_failure = "carrier_failure"
    system_outage = "system_outage"
    return_dispute = "return_dispute"
    sla_breach = "sla_breach"


class SeverityEnum(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class ResponsibleAreaEnum(str, Enum):
    warehouse_operations = "warehouse_operations"
    last_mile_carrier = "last_mile_carrier"
    reverse_logistics = "reverse_logistics"
    customer_experience = "customer_experience"
    commercial = "commercial"
    technology = "technology"


class IncidentStatusEnum(str, Enum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    reopened = "reopened"


class WarehouseLocationEnum(str, Enum):
    los_angeles = "los_angeles"
    zaragoza = "zaragoza"


# ──────────────────────── Transitions ────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    "open": {"assigned"},
    "assigned": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": {"closed", "reopened"},
    "reopened": set(),
    "closed": set(),
}


def is_valid_transition(current: str, next_status: str) -> bool:
    return next_status in VALID_TRANSITIONS.get(current, set())


# ──────────────────────── Request schemas ────────────────────────


class IncidentCreate(BaseModel):
    warehouse_location: Optional[WarehouseLocationEnum] = None
    client_name: Optional[str] = None
    channel: ChannelEnum
    type: IncidentTypeEnum
    severity: SeverityEnum
    responsible_area: ResponsibleAreaEnum
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    assigned_to: Optional[str] = None


class IncidentUpdate(BaseModel):
    warehouse_location: Optional[WarehouseLocationEnum] = None
    client_name: Optional[str] = None
    channel: Optional[ChannelEnum] = None
    type: Optional[IncidentTypeEnum] = None
    severity: Optional[SeverityEnum] = None
    responsible_area: Optional[ResponsibleAreaEnum] = None
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, min_length=1)
    assigned_to: Optional[str] = None
    author: str = Field(..., min_length=1)


class StatusTransition(BaseModel):
    status: IncidentStatusEnum
    author: str = Field(..., min_length=1)


# ──────────────────────── Response schemas ────────────────────────


class AuditLogEntry(BaseModel):
    id: str
    incident_id: str
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: str
    changed_at: str


class IncidentResponse(BaseModel):
    id: str
    warehouse_location: Optional[str] = None
    client_name: Optional[str] = None
    channel: str
    type: str
    severity: str
    responsible_area: str
    title: str
    description: str
    status: str
    assigned_to: Optional[str] = None
    created_at: str
    updated_at: str


class IncidentDetailResponse(IncidentResponse):
    audit_log: list[AuditLogEntry] = []


class OpenBySeverityEntry(BaseModel):
    severity: str
    count: int


class OpenBySeverityResponse(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class ErrorResponse(BaseModel):
    detail: str


# ──────────────────────── Helpers ────────────────────────


def generate_id() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()