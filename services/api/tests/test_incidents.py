"""
Comprehensive tests for TrackFlow Incident Manager API.
Uses TestClient from FastAPI with an isolated in-memory SQLite database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from database import get_connection, init_db

from main import app


@pytest.fixture(autouse=True)
def db():
    """Ensure clean tables before each test."""
    conn = get_connection()
    init_db(conn)
    conn.execute("DELETE FROM incident_audit_log")
    conn.execute("DELETE FROM incidents")
    conn.execute("DELETE FROM metadata")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def client():
    """Return a TestClient with clean DB per test (via autouse db fixture)."""
    return TestClient(app)


# ──────────────────────── Health ────────────────────────


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_method_not_allowed(self, client):
        resp = client.post("/health")
        assert resp.status_code == 405


# ──────────────────────── Create Incident ────────────────────────


class TestCreateIncident:
    CREATE_PAYLOAD = {
        "warehouse_location": "los_angeles",
        "client_name": "TestClient",
        "channel": "client_email",
        "type": "lost_parcel",
        "severity": "high",
        "responsible_area": "last_mile_carrier",
        "title": "Test incident creation",
        "description": "Testing the creation endpoint.",
        "assigned_to": None,
        "author": "system",
    }

    def test_create_minimal(self, client):
        payload = {k: v for k, v in self.CREATE_PAYLOAD.items() if k != "warehouse_location"}
        resp = client.post("/api/incidents", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "open"
        assert data["type"] == "lost_parcel"
        assert data["severity"] == "high"
        assert data["warehouse_location"] is None
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_full(self, client):
        resp = client.post("/api/incidents", json=self.CREATE_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["warehouse_location"] == "los_angeles"
        assert data["client_name"] == "TestClient"
        assert data["channel"] == "client_email"
        assert data["title"] == "Test incident creation"
        assert data["assigned_to"] is None

    def test_create_with_assigned_to(self, client):
        payload = {**self.CREATE_PAYLOAD, "assigned_to": "John Doe"}
        resp = client.post("/api/incidents", json=payload)
        assert resp.status_code == 201
        assert resp.json()["assigned_to"] == "John Doe"

    def test_create_missing_required_field(self, client):
        payload = {k: v for k, v in self.CREATE_PAYLOAD.items() if k != "channel"}
        resp = client.post("/api/incidents", json=payload)
        assert resp.status_code == 422

    def test_create_empty_title(self, client):
        payload = {**self.CREATE_PAYLOAD, "title": ""}
        resp = client.post("/api/incidents", json=payload)
        assert resp.status_code == 422

    def test_create_invalid_enum(self, client):
        payload = {**self.CREATE_PAYLOAD, "severity": "ultra_critical"}
        resp = client.post("/api/incidents", json=payload)
        assert resp.status_code == 422

    def test_create_null_client_name(self, client):
        payload = {**self.CREATE_PAYLOAD, "client_name": None}
        resp = client.post("/api/incidents", json=payload)
        assert resp.status_code == 201
        assert resp.json()["client_name"] is None


# ──────────────────────── List Incidents ────────────────────────


class TestListIncidents:
    def test_list_empty(self, client):
        resp = client.get("/api/incidents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self, client):
        client.post("/api/incidents", json={
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "low",
            "responsible_area": "warehouse_operations",
            "title": "Test A",
            "description": "Desc A",
            "author": "system",
        })
        client.post("/api/incidents", json={
            "channel": "client_email",
            "type": "sla_breach",
            "severity": "critical",
            "responsible_area": "technology",
            "title": "Test B",
            "description": "Desc B",
            "author": "system",
        })
        resp = client.get("/api/incidents")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_filter_by_status(self, client):
        client.post("/api/incidents", json={
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "low",
            "responsible_area": "warehouse_operations",
            "title": "Open incident",
            "description": "Desc",
            "assigned_to": None,
            "author": "system",
        })
        client.post("/api/incidents", json={
            "channel": "client_email",
            "type": "sla_breach",
            "severity": "critical",
            "responsible_area": "technology",
            "title": "Will be assigned",
            "description": "Desc",
            "assigned_to": None,
            "author": "system",
        })
        # Transition first one (most recent) to assigned
        # API returns ordered by created_at DESC, so [0] is "Will be assigned"
        all_incidents = client.get("/api/incidents").json()
        client.patch(f"/api/incidents/{all_incidents[0]['id']}/status",
                     json={"status": "assigned", "author": "tester"})

        resp = client.get("/api/incidents?status=open")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "Open incident"

    def test_list_filter_by_severity(self, client):
        client.post("/api/incidents", json={
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "low",
            "responsible_area": "warehouse_operations",
            "title": "Low severity",
            "description": "Desc",
            "author": "system",
        })
        client.post("/api/incidents", json={
            "channel": "client_email",
            "type": "sla_breach",
            "severity": "critical",
            "responsible_area": "technology",
            "title": "Critical severity",
            "description": "Desc",
            "author": "system",
        })
        resp = client.get("/api/incidents?severity=low")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["severity"] == "low"

    def test_list_filter_by_responsible_area(self, client):
        client.post("/api/incidents", json={
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "low",
            "responsible_area": "warehouse_operations",
            "title": "Ops incident",
            "description": "Desc",
            "author": "system",
        })
        client.post("/api/incidents", json={
            "channel": "client_email",
            "type": "sla_breach",
            "severity": "critical",
            "responsible_area": "technology",
            "title": "Tech incident",
            "description": "Desc",
            "author": "system",
        })
        resp = client.get("/api/incidents?responsible_area=technology")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["responsible_area"] == "technology"

    def test_list_filter_multiple(self, client):
        client.post("/api/incidents", json={
            "warehouse_location": "los_angeles",
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "low",
            "responsible_area": "warehouse_operations",
            "title": "LA Ops low",
            "description": "Desc",
            "author": "system",
        })
        client.post("/api/incidents", json={
            "warehouse_location": "zaragoza",
            "channel": "client_email",
            "type": "sla_breach",
            "severity": "critical",
            "responsible_area": "technology",
            "title": "ZGZ Tech critical",
            "description": "Desc",
            "author": "system",
        })
        resp = client.get("/api/incidents?severity=low&responsible_area=warehouse_operations")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


# ──────────────────────── Get Single Incident ────────────────────────


class TestGetIncident:
    def test_get_existing(self, client):
        create_resp = client.post("/api/incidents", json={
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "low",
            "responsible_area": "warehouse_operations",
            "title": "Single incident",
            "description": "Desc",
            "author": "system",
        })
        inc_id = create_resp.json()["id"]
        resp = client.get(f"/api/incidents/{inc_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == inc_id

    def test_get_nonexistent(self, client):
        resp = client.get("/api/incidents/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Incident not found"

    def test_get_includes_audit_log_field(self, client):
        create_resp = client.post("/api/incidents", json={
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "low",
            "responsible_area": "warehouse_operations",
            "title": "With audit field",
            "description": "Desc",
            "author": "system",
        })
        inc_id = create_resp.json()["id"]
        resp = client.get(f"/api/incidents/{inc_id}")
        assert resp.status_code == 200
        assert "audit_log" in resp.json()
        assert resp.json()["audit_log"] == []


# ──────────────────────── Update Incident ────────────────────────


class TestUpdateIncident:
    @pytest.fixture
    def inc_id(self, client):
        resp = client.post("/api/incidents", json={
            "warehouse_location": "los_angeles",
            "client_name": "OriginalCo",
            "channel": "client_email",
            "type": "lost_parcel",
            "severity": "high",
            "responsible_area": "last_mile_carrier",
            "title": "Original title",
            "description": "Original description",
            "assigned_to": "OriginalUser",
            "author": "system",
        })
        return resp.json()["id"]

    def test_update_title(self, client, inc_id):
        resp = client.put(f"/api/incidents/{inc_id}", json={
            "title": "Updated title",
            "author": "manager",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated title"

    def test_update_responsible_area_creates_audit(self, client, inc_id):
        resp = client.put(f"/api/incidents/{inc_id}", json={
            "responsible_area": "customer_experience",
            "author": "manager",
        })
        assert resp.status_code == 200
        # Fetch full detail to see audit log
        detail = client.get(f"/api/incidents/{inc_id}").json()
        audit_log = detail["audit_log"]
        relevant = [e for e in audit_log if e["field_changed"] == "responsible_area"]
        assert len(relevant) == 1
        assert relevant[0]["old_value"] == "last_mile_carrier"
        assert relevant[0]["new_value"] == "customer_experience"
        assert relevant[0]["changed_by"] == "manager"

    def test_update_assigned_to_creates_audit(self, client, inc_id):
        resp = client.put(f"/api/incidents/{inc_id}", json={
            "assigned_to": "NewAssignee",
            "author": "manager",
        })
        assert resp.status_code == 200
        detail = client.get(f"/api/incidents/{inc_id}").json()
        relevant = [e for e in detail["audit_log"] if e["field_changed"] == "assigned_to"]
        assert len(relevant) == 1
        assert relevant[0]["old_value"] == "OriginalUser"
        assert relevant[0]["new_value"] == "NewAssignee"

    def test_update_non_audited_field_no_audit(self, client, inc_id):
        client.put(f"/api/incidents/{inc_id}", json={
            "description": "Updated description",
            "author": "manager",
        })
        detail = client.get(f"/api/incidents/{inc_id}").json()
        assert len(detail["audit_log"]) == 0

    def test_update_nonexistent(self, client):
        resp = client.put("/api/incidents/nonexistent", json={
            "title": "Nope",
            "author": "test",
        })
        assert resp.status_code == 404

    def test_update_no_changes_returns_original(self, client, inc_id):
        resp = client.put(f"/api/incidents/{inc_id}", json={
            "title": "Original title",
            "author": "manager",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Original title"

    def test_update_without_author_fails(self, client, inc_id):
        resp = client.put(f"/api/incidents/{inc_id}", json={
            "title": "No author",
        })
        assert resp.status_code == 422


# ──────────────────────── Status Transitions ────────────────────────


class TestStatusTransitions:
    @pytest.fixture
    def inc_id(self, client):
        resp = client.post("/api/incidents", json={
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "high",
            "responsible_area": "warehouse_operations",
            "title": "Transition test",
            "description": "Testing transitions",
            "author": "system",
        })
        return resp.json()["id"]

    def _transition(self, client, inc_id, status, author="tester"):
        return client.patch(f"/api/incidents/{inc_id}/status",
                            json={"status": status, "author": author})

    def test_open_to_assigned(self, client, inc_id):
        resp = self._transition(client, inc_id, "assigned")
        assert resp.status_code == 200
        assert resp.json()["status"] == "assigned"

    def test_assigned_to_in_progress(self, client, inc_id):
        self._transition(client, inc_id, "assigned")
        resp = self._transition(client, inc_id, "in_progress")
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_full_chain_to_closed(self, client, inc_id):
        for status in ("assigned", "in_progress", "resolved", "closed"):
            resp = self._transition(client, inc_id, status)
            assert resp.status_code == 200, f"Failed at {status}: {resp.json()}"
        assert resp.json()["status"] == "closed"

    def test_resolved_to_reopened(self, client, inc_id):
        self._transition(client, inc_id, "assigned")
        self._transition(client, inc_id, "in_progress")
        self._transition(client, inc_id, "resolved")
        resp = self._transition(client, inc_id, "reopened")
        assert resp.status_code == 200
        assert resp.json()["status"] == "reopened"

    def test_open_to_closed_invalid(self, client, inc_id):
        resp = self._transition(client, inc_id, "closed")
        assert resp.status_code == 422
        assert "Invalid transition" in resp.json()["detail"]

    def test_closed_to_any_invalid(self, client, inc_id):
        for status in ("assigned", "in_progress", "resolved"):
            resp = self._transition(client, inc_id, status)
            assert resp.status_code == 200, f"Failed at {status}"
        resp = self._transition(client, inc_id, "closed")
        assert resp.status_code == 200
        # Now try to leave closed
        resp = self._transition(client, inc_id, "open")
        assert resp.status_code == 422
        assert "Invalid transition" in resp.json()["detail"]

    def test_reopened_to_any_invalid(self, client, inc_id):
        self._transition(client, inc_id, "assigned")
        self._transition(client, inc_id, "in_progress")
        self._transition(client, inc_id, "resolved")
        self._transition(client, inc_id, "reopened")
        for status in ("open", "assigned", "in_progress", "resolved", "closed"):
            resp = self._transition(client, inc_id, status)
            assert resp.status_code == 422, f"Should not allow {status}: {resp.json()}"

    def test_status_transition_creates_audit(self, client, inc_id):
        self._transition(client, inc_id, "assigned", author="operator1")
        detail = client.get(f"/api/incidents/{inc_id}").json()
        relevant = [e for e in detail["audit_log"] if e["field_changed"] == "status"]
        assert len(relevant) == 1
        assert relevant[0]["old_value"] == "open"
        assert relevant[0]["new_value"] == "assigned"
        assert relevant[0]["changed_by"] == "operator1"

    def test_invalid_transition_nonexistent_incident(self, client):
        resp = client.patch("/api/incidents/nonexistent/status",
                            json={"status": "assigned", "author": "test"})
        assert resp.status_code == 404

    def test_transition_without_author_fails(self, client, inc_id):
        resp = client.patch(f"/api/incidents/{inc_id}/status",
                            json={"status": "assigned"})
        assert resp.status_code == 422


# ──────────────────────── Open by Severity ────────────────────────


class TestOpenBySeverity:
    def test_empty_returns_zeros(self, client):
        resp = client.get("/api/incidents/open-by-severity")
        assert resp.status_code == 200
        assert resp.json() == {"critical": 0, "high": 0, "medium": 0, "low": 0}

    def test_counts_open_only(self, client):
        def _path_to(target):
            path = {"assigned": ["assigned"],
                    "resolved": ["assigned", "in_progress", "resolved"],
                    "closed": ["assigned", "in_progress", "resolved", "closed"]}
            return path.get(target, [])

        def create(severity, final_status="open"):
            resp = client.post("/api/incidents", json={
                "channel": "dashboard",
                "type": "inventory_discrepancy",
                "severity": severity,
                "responsible_area": "warehouse_operations",
                "title": f"{severity} incident",
                "description": "Desc",
                "author": "system",
            })
            inc_id = resp.json()["id"]
            if final_status != "open":
                for st in _path_to(final_status):
                    client.patch(f"/api/incidents/{inc_id}/status",
                                 json={"status": st, "author": "tester"})
            return inc_id

        # Create incidents
        create("critical")  # open → counted
        create("critical", "closed")  # closed → NOT counted
        create("high")  # open → counted
        create("high", "resolved")  # resolved → NOT counted
        create("medium")  # open → counted
        create("low")  # open → counted

        resp = client.get("/api/incidents/open-by-severity")
        assert resp.status_code == 200
        data = resp.json()
        assert data["critical"] == 1, f"Expected 1, got {data}"
        assert data["high"] == 1, f"Expected 1, got {data}"
        assert data["medium"] == 1, f"Expected 1, got {data}"
        assert data["low"] == 1, f"Expected 1, got {data}"

    def test_key_names_match(self, client):
        client.post("/api/incidents", json={
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "critical",
            "responsible_area": "warehouse_operations",
            "title": "Critical",
            "description": "Desc",
            "author": "system",
        })
        resp = client.get("/api/incidents/open-by-severity")
        data = resp.json()
        for key in ("critical", "high", "medium", "low"):
            assert key in data


# ──────────────────────── Edge Cases ────────────────────────


class TestEdgeCases:
    def test_null_warehouse_location(self, client):
        resp = client.post("/api/incidents", json={
            "warehouse_location": None,
            "client_name": "NoWarehouse",
            "channel": "wms_alert",
            "type": "system_outage",
            "severity": "critical",
            "responsible_area": "technology",
            "title": "No location",
            "description": "Test null location",
            "author": "system",
        })
        assert resp.status_code == 201
        assert resp.json()["warehouse_location"] is None

    def test_null_client_name(self, client):
        resp = client.post("/api/incidents", json={
            "client_name": None,
            "channel": "client_email",
            "type": "return_dispute",
            "severity": "medium",
            "responsible_area": "reverse_logistics",
            "title": "No client",
            "description": "Test null client",
            "author": "system",
        })
        assert resp.status_code == 201
        assert resp.json()["client_name"] is None

    def test_null_assigned_to(self, client):
        resp = client.post("/api/incidents", json={
            "channel": "warehouse_call",
            "type": "carrier_failure",
            "severity": "high",
            "responsible_area": "last_mile_carrier",
            "title": "Unassigned",
            "description": "Test unassigned",
            "assigned_to": None,
            "author": "system",
        })
        assert resp.status_code == 201
        assert resp.json()["assigned_to"] is None

    def test_all_channels(self, client):
        channels = ["wms_alert", "client_email", "carrier_portal_alert", "warehouse_call", "dashboard"]
        for ch in channels:
            resp = client.post("/api/incidents", json={
                "channel": ch,
                "type": "inventory_discrepancy",
                "severity": "low",
                "responsible_area": "warehouse_operations",
                "title": f"Channel {ch}",
                "description": "Desc",
                "author": "system",
            })
            assert resp.status_code == 201, f"Failed for channel {ch}: {resp.json()}"

    def test_all_types(self, client):
        types = ["lost_parcel", "inventory_discrepancy", "carrier_failure", "system_outage", "return_dispute", "sla_breach"]
        for t in types:
            resp = client.post("/api/incidents", json={
                "channel": "dashboard",
                "type": t,
                "severity": "low",
                "responsible_area": "warehouse_operations",
                "title": f"Type {t}",
                "description": "Desc",
                "author": "system",
            })
            assert resp.status_code == 201, f"Failed for type {t}: {resp.json()}"

    def test_all_severities(self, client):
        severities = ["critical", "high", "medium", "low"]
        for s in severities:
            resp = client.post("/api/incidents", json={
                "channel": "dashboard",
                "type": "inventory_discrepancy",
                "severity": s,
                "responsible_area": "warehouse_operations",
                "title": f"Severity {s}",
                "description": "Desc",
                "author": "system",
            })
            assert resp.status_code == 201, f"Failed for severity {s}: {resp.json()}"

    def test_all_areas(self, client):
        areas = ["warehouse_operations", "last_mile_carrier", "reverse_logistics", "customer_experience", "commercial", "technology"]
        for a in areas:
            resp = client.post("/api/incidents", json={
                "channel": "dashboard",
                "type": "inventory_discrepancy",
                "severity": "low",
                "responsible_area": a,
                "title": f"Area {a}",
                "description": "Desc",
                "author": "system",
            })
            assert resp.status_code == 201, f"Failed for area {a}: {resp.json()}"

    def test_both_warehouses(self, client):
        for loc in ["los_angeles", "zaragoza"]:
            resp = client.post("/api/incidents", json={
                "warehouse_location": loc,
                "channel": "dashboard",
                "type": "inventory_discrepancy",
                "severity": "low",
                "responsible_area": "warehouse_operations",
                "title": f"Warehouse {loc}",
                "description": "Desc",
                "author": "system",
            })
            assert resp.status_code == 201, f"Failed for location {loc}: {resp.json()}"
            assert resp.json()["warehouse_location"] == loc

    def test_zaragoza_location(self, client):
        resp = client.post("/api/incidents", json={
            "warehouse_location": "zaragoza",
            "channel": "dashboard",
            "type": "inventory_discrepancy",
            "severity": "low",
            "responsible_area": "warehouse_operations",
            "title": "Zaragoza incident",
            "description": "Desc",
            "author": "system",
        })
        assert resp.status_code == 201
        assert resp.json()["warehouse_location"] == "zaragoza"