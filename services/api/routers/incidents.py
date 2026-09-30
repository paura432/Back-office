"""
Routers for incident CRUD, transitions, audit, and aggregation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import (
    IncidentCreate,
    IncidentDetailResponse,
    IncidentResponse,
    IncidentUpdate,
    OpenBySeverityResponse,
    StatusTransition,
    generate_id,
    is_valid_transition,
    utc_now,
    IncidentStatusEnum,
    SeverityEnum,
    ResponsibleAreaEnum,
)
from database import get_connection

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def incident_row_to_response(row: dict) -> dict:
    """Convert a DB row dict to an IncidentResponse-compatible dict."""
    return {
        "id": row["id"],
        "warehouse_location": row.get("warehouse_location"),
        "client_name": row.get("client_name"),
        "channel": row["channel"],
        "type": row["type"],
        "severity": row["severity"],
        "responsible_area": row["responsible_area"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "assigned_to": row.get("assigned_to"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def fetch_audit_log(conn, incident_id: str) -> list[dict]:
    cursor = conn.execute(
        "SELECT * FROM incident_audit_log WHERE incident_id = ? ORDER BY changed_at ASC",
        (incident_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


# ──────────────────────── Endpoints ────────────────────────


@router.get("", response_model=list[IncidentResponse])
def list_incidents(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    responsible_area: str | None = Query(None),
    db=Depends(get_db),
):
    # Validate enum filters
    if status is not None and status not in IncidentStatusEnum._value2member_map_:
        raise HTTPException(status_code=422, detail=f"Invalid status: {status}")
    if severity is not None and severity not in SeverityEnum._value2member_map_:
        raise HTTPException(status_code=422, detail=f"Invalid severity: {severity}")
    if responsible_area is not None and responsible_area not in ResponsibleAreaEnum._value2member_map_:
        raise HTTPException(status_code=422, detail=f"Invalid responsible_area: {responsible_area}")

    query = "SELECT * FROM incidents WHERE 1=1"
    params: list[str] = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if responsible_area:
        query += " AND responsible_area = ?"
        params.append(responsible_area)
    query += " ORDER BY created_at DESC"
    rows = db.execute(query, params).fetchall()
    return [incident_row_to_response(dict(r)) for r in rows]


@router.get("/open-by-severity", response_model=OpenBySeverityResponse)
def open_by_severity(db=Depends(get_db)):
    rows = db.execute(
        """
        SELECT severity, COUNT(*) as count
        FROM incidents
        WHERE status NOT IN ('resolved', 'closed')
        GROUP BY severity
        """
    ).fetchall()
    result = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in rows:
        result[r["severity"]] = r["count"]
    return result


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: str, db=Depends(get_db)):
    row = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = incident_row_to_response(dict(row))
    audit = fetch_audit_log(db, incident_id)
    return IncidentDetailResponse(**incident, audit_log=audit)


@router.post("", response_model=IncidentResponse, status_code=201)
def create_incident(payload: IncidentCreate, db=Depends(get_db)):
    now = utc_now()
    inc_id = generate_id()
    db.execute(
        """
        INSERT INTO incidents (id, warehouse_location, client_name, channel, type, severity,
                               responsible_area, title, description, status, assigned_to, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
        """,
        (
            inc_id,
            payload.warehouse_location.value if payload.warehouse_location else None,
            payload.client_name,
            payload.channel.value,
            payload.type.value,
            payload.severity.value,
            payload.responsible_area.value,
            payload.title,
            payload.description,
            payload.assigned_to,
            now,
            now,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM incidents WHERE id = ?", (inc_id,)).fetchone()
    return incident_row_to_response(dict(row))


@router.put("/{incident_id}", response_model=IncidentResponse)
def update_incident(incident_id: str, payload: IncidentUpdate, db=Depends(get_db)):
    row = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    current = dict(row)
    now = utc_now()
    updates: list[str] = []
    params: list[str | None] = []

    # Map Pydantic field → DB column (same name here, but explicit for clarity)
    UPDATABLE_FIELDS = {
        "warehouse_location": lambda v: v.value if v else None,
        "client_name": lambda v: v,
        "channel": lambda v: v.value if v else None,
        "type": lambda v: v.value if v else None,
        "severity": lambda v: v.value if v else None,
        "responsible_area": lambda v: v.value if v else None,
        "title": lambda v: v,
        "description": lambda v: v,
        "assigned_to": lambda v: v,
    }

    # Fields that generate audit trail when changed
    AUDIT_FIELDS = {"assigned_to", "responsible_area"}

    for field, converter in UPDATABLE_FIELDS.items():
        if field not in payload.model_fields_set:
            continue  # field was not sent → do not touch
        new_val = converter(getattr(payload, field))
        old_val = current.get(field)
        # Compare explicitly
        if old_val == new_val:
            continue  # no real change → skip

        updates.append(f"{field} = ?")
        params.append(new_val)

        if field in AUDIT_FIELDS:
            db.execute(
                """
                INSERT INTO incident_audit_log (id, incident_id, field_changed, old_value, new_value, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generate_id(),
                    incident_id,
                    field,
                    str(old_val) if old_val is not None else None,
                    str(new_val) if new_val is not None else None,
                    payload.author,
                    now,
                ),
            )

    if not updates:
        return incident_row_to_response(current)

    updates.append("updated_at = ?")
    params.append(now)
    params.append(incident_id)

    db.execute(
        f"UPDATE incidents SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    db.commit()

    row = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    return incident_row_to_response(dict(row))


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def transition_status(incident_id: str, payload: StatusTransition, db=Depends(get_db)):
    row = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    current = dict(row)
    current_status = current["status"]
    next_status = payload.status.value

    if not is_valid_transition(current_status, next_status):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid transition: {current_status} → {next_status}",
        )

    now = utc_now()
    db.execute(
        "UPDATE incidents SET status = ?, updated_at = ? WHERE id = ?",
        (next_status, now, incident_id),
    )
    db.execute(
        """
        INSERT INTO incident_audit_log (id, incident_id, field_changed, old_value, new_value, changed_by, changed_at)
        VALUES (?, ?, 'status', ?, ?, ?, ?)
        """,
        (generate_id(), incident_id, current_status, next_status, payload.author, now),
    )
    db.commit()

    row = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    return incident_row_to_response(dict(row))