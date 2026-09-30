"""
Routers for incident CRUD, transitions, audit, and aggregation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import (
    AuditLogEntry,
    ErrorResponse,
    IncidentCreate,
    IncidentDetailResponse,
    IncidentResponse,
    IncidentUpdate,
    OpenBySeverityResponse,
    StatusTransition,
    generate_id,
    is_valid_transition,
    utc_now,
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


def fetch_audit_log(cursor, incident_id: str) -> list[dict]:
    cursor.execute(
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

    # Fields that can be updated
    UPDATABLE_FIELDS = [
        "warehouse_location",
        "client_name",
        "channel",
        "type",
        "severity",
        "responsible_area",
        "title",
        "description",
        "assigned_to",
    ]

    for field in UPDATABLE_FIELDS:
        new_val = getattr(payload, field, None)
        if new_val is not None:
            # Convert enum to value if needed
            if hasattr(new_val, "value"):
                new_val = new_val.value
            old_val = current.get(field)
            if str(new_val) != str(old_val) if old_val else True:
                updates.append(f"{field} = ?")
                params.append(new_val)
                # Audit tracked fields
                if field in ("assigned_to", "responsible_area"):
                    db.execute(
                        """
                        INSERT INTO incident_audit_log (id, incident_id, field_changed, old_value, new_value, changed_by, changed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            generate_id(),
                            incident_id,
                            field,
                            str(old_val) if old_val else None,
                            str(new_val),
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

    # Critical rule: cannot go directly to closed without passing through resolved
    # This is already enforced by the graph, but add explicit check
    if current["severity"] == "critical" and next_status == "closed":
        raise HTTPException(
            status_code=422,
            detail="Critical incidents cannot transition directly to closed. Must pass through resolved first.",
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