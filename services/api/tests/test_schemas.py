"""
Tests de serialización y validación de schemas Pydantic.
Verifica que los contratos de entrada/salida sean correctos y seguros.
"""
import pytest
from pydantic import ValidationError

from app.schemas.health import HealthResponse
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserProfileResponse,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    MessageResponse,
)
from app.schemas.inventory import (
    InventoryItemSummary,
    InventoryItemDetail,
    InventoryAlert,
)
from app.schemas.orders import (
    OrderCreateRequest,
    OrderItemInput,
    OrderItemSummary,
    OrderSummary,
    OrderDetail,
    OrderStatusUpdate,
)
from app.schemas.shipments import (
    TrackingEvent,
    ShipmentSummary,
    ShipmentDetail,
    CarrierRecommendationRequest,
    CarrierRecommendation,
)
from app.schemas.returns import (
    ReturnRequestInput,
    ReturnRequestSummary,
    ReturnRequestDetail,
    ReturnApproval,
    ReturnInspectionResult,
)
from app.schemas.customers import (
    CustomerSummary,
    CustomerDetail,
    CustomerHealthScore,
)
from app.schemas.dashboard import (
    DashboardKPI,
    ExecutiveDashboard,
    WeeklyReport,
)
from app.schemas.users import (
    UserCreate,
    UserUpdate,
    UserSummary,
    UserDetail,
)


# ── Health ─────────────────────────────────────────────────────────────

class TestHealthSchema:
    def test_health_response_schema(self):
        resp = HealthResponse(status="ok")
        data = resp.model_dump()
        assert data == {"status": "ok"}

    def test_health_default(self):
        resp = HealthResponse()
        assert resp.status == "ok"


# ── Auth ───────────────────────────────────────────────────────────────

class TestAuthSchemas:
    def test_register_request_valid(self):
        body = RegisterRequest(
            email="user@example.com",
            password="SecurePass1",
            full_name="Test User",
        )
        assert body.email == "user@example.com"

    def test_register_request_weak_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="weak",  # too short, no uppercase, no digit
                full_name="Test User",
            )

    def test_register_request_no_uppercase(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="lowercase1",
                full_name="Test User",
            )

    def test_register_request_no_digit(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="SecurePass",
                full_name="Test User",
            )

    def test_login_request_valid(self):
        body = LoginRequest(email="user@example.com", password="secret")
        assert body.email == "user@example.com"

    def test_login_request_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="not-an-email", password="secret")

    def test_token_response(self):
        resp = TokenResponse(access_token="abc123")
        data = resp.model_dump()
        assert data["access_token"] == "abc123"
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        # Security: must not expose password or hash
        assert "password" not in data
        assert "hash" not in data

    def test_user_profile_response_no_password(self):
        """Verify that UserProfileResponse never contains password fields."""
        resp = UserProfileResponse(id=1, email="a@b.com", full_name="A", is_active=True)
        data = resp.model_dump()
        assert "password" not in data
        assert "password_hash" not in data
        assert "salt" not in data
        assert "reset_token" not in data
        assert data["id"] == 1
        assert data["email"] == "a@b.com"

    def test_password_recovery_request(self):
        body = PasswordRecoveryRequest(email="user@example.com")
        assert body.email == "user@example.com"

    def test_password_reset_request_valid(self):
        body = PasswordResetRequest(token="tok123", new_password="NewPass123")
        assert body.token == "tok123"

    def test_password_reset_weak(self):
        with pytest.raises(ValidationError):
            PasswordResetRequest(token="tok123", new_password="weak")

    def test_message_response(self):
        resp = MessageResponse(message="ok")
        assert resp.message == "ok"


# ── Inventory ──────────────────────────────────────────────────────────

class TestInventorySchemas:
    def test_inventory_summary(self):
        item = InventoryItemSummary(
            sku="SKU-001", name="Widget", warehouse="LA", quantity=42
        )
        data = item.model_dump()
        assert data["sku"] == "SKU-001"
        assert data["quantity"] == 42

    def test_inventory_summary_negative_quantity(self):
        with pytest.raises(ValidationError):
            InventoryItemSummary(
                sku="SKU-001", name="Widget", warehouse="LA", quantity=-1
            )

    def test_inventory_detail(self):
        detail = InventoryItemDetail(
            sku="SKU-001", name="Widget", description="A widget",
            warehouse="LA", quantity=10,
        )
        assert detail.description == "A widget"

    def test_inventory_alert(self):
        alert = InventoryAlert(
            sku="SKU-001", name="Widget", warehouse="LA",
            current_quantity=5, threshold=10,
        )
        assert alert.current_quantity < alert.threshold


# ── Orders ─────────────────────────────────────────────────────────────

class TestOrderSchemas:
    def test_order_item_input(self):
        item = OrderItemInput(sku="SKU-001", quantity=3)
        assert item.quantity == 3

    def test_order_item_input_zero_quantity(self):
        with pytest.raises(ValidationError):
            OrderItemInput(sku="SKU-001", quantity=0)

    def test_order_create_request(self):
        req = OrderCreateRequest(
            client_id=1,
            items=[OrderItemInput(sku="SKU-001", quantity=2)],
            shipping_address="123 Main St",
        )
        assert len(req.items) == 1

    def test_order_summary(self):
        from datetime import datetime
        summary = OrderSummary(
            id=1, client_name="Acme", status="pending",
            item_count=3, created_at=datetime.now(),
        )
        assert summary.client_name == "Acme"

    def test_order_status_update(self):
        update = OrderStatusUpdate(status="shipped")
        assert update.status == "shipped"


# ── Shipments ──────────────────────────────────────────────────────────

class TestShipmentSchemas:
    def test_tracking_event(self):
        from datetime import datetime
        event = TrackingEvent(
            timestamp=datetime.now(), location="LA Hub",
            status="in_transit", description="Package in transit",
        )
        assert event.status == "in_transit"

    def test_shipment_summary(self):
        summary = ShipmentSummary(
            id=1, tracking_number="1Z999AA1", carrier="UPS",
            recipient="John", status="in_transit",
        )
        assert summary.carrier == "UPS"

    def test_carrier_recommendation_request(self):
        req = CarrierRecommendationRequest(
            destination="Madrid", weight_kg=5.0, urgency="high",
        )
        assert req.urgency == "high"

    def test_carrier_recommendation(self):
        rec = CarrierRecommendation(
            carrier="UPS", estimated_cost=12.50,
            estimated_days=3, confidence_score=0.95,
        )
        assert 0 <= rec.confidence_score <= 1

    def test_carrier_recommendation_invalid_urgency(self):
        with pytest.raises(ValidationError):
            CarrierRecommendationRequest(
                destination="Madrid", weight_kg=5.0, urgency="urgent",
            )


# ── Returns ────────────────────────────────────────────────────────────

class TestReturnSchemas:
    def test_return_request_input(self):
        req = ReturnRequestInput(order_id=1, sku="SKU-001", quantity=1, reason="Damaged")
        assert req.reason == "Damaged"

    def test_return_approval(self):
        approval = ReturnApproval(approved=True)
        assert approval.approved is True

    def test_return_inspection_result_valid(self):
        result = ReturnInspectionResult(condition="good")
        assert result.condition == "good"

    def test_return_inspection_result_invalid_condition(self):
        with pytest.raises(ValidationError):
            ReturnInspectionResult(condition="unknown")

    def test_return_request_summary(self):
        from datetime import datetime
        summary = ReturnRequestSummary(
            id=1, order_id=1, sku="SKU-001", status="pending",
            created_at=datetime.now(),
        )
        assert summary.status == "pending"


# ── Customers ──────────────────────────────────────────────────────────

class TestCustomerSchemas:
    def test_customer_summary(self):
        c = CustomerSummary(
            id=1, company_name="Acme Corp", contact_email="a@b.com", country="US",
        )
        assert c.is_active is True

    def test_customer_detail(self):
        c = CustomerDetail(
            id=1, company_name="Acme Corp", contact_email="a@b.com", country="US",
        )
        assert c.contact_name == ""

    def test_customer_health_score(self):
        h = CustomerHealthScore(
            customer_id=1, company_name="Acme Corp",
            health_score=85.0, risk_level="low",
        )
        assert h.risk_level == "low"

    def test_customer_health_score_invalid_risk(self):
        with pytest.raises(ValidationError):
            CustomerHealthScore(
                customer_id=1, company_name="Acme Corp",
                health_score=50.0, risk_level="unknown",
            )


# ── Users ──────────────────────────────────────────────────────────────

class TestUserSchemas:
    def test_user_create(self):
        u = UserCreate(
            email="a@b.com", password="Secure12", full_name="A", role="operator",
        )
        assert u.role == "operator"

    def test_user_create_invalid_role(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="a@b.com", password="Secure12", full_name="A", role="superadmin",
            )

    def test_user_update(self):
        u = UserUpdate(full_name="New Name")
        assert u.full_name == "New Name"

    def test_user_summary(self):
        u = UserSummary(id=1, email="a@b.com", full_name="A", role="admin", is_active=True)
        data = u.model_dump()
        assert "password" not in data

    def test_user_detail(self):
        u = UserDetail(id=1, email="a@b.com", full_name="A", role="admin", is_active=True, created_at="2026-01-01")
        data = u.model_dump()
        # Security: must not include password
        assert "password" not in data
        assert "password_hash" not in data


# ── Dashboard ──────────────────────────────────────────────────────────

class TestDashboardSchemas:
    def test_dashboard_kpi(self):
        kpi = DashboardKPI(label="Shipments", value=1500, unit="units")
        assert kpi.value == 1500

    def test_dashboard_kpi_trend(self):
        kpi = DashboardKPI(
            label="On-time rate", value=95.5, unit="%",
            previous_value=94.0, trend="up",
        )
        assert kpi.trend == "up"

    def test_dashboard_kpi_invalid_trend(self):
        with pytest.raises(ValidationError):
            DashboardKPI(label="Test", value=1, trend="sideways")

    def test_executive_dashboard(self):
        from app.schemas.dashboard import DashboardKPI
        dash = ExecutiveDashboard(
            total_shipments=DashboardKPI(label="Total", value=1000),
            on_time_rate=DashboardKPI(label="OT Rate", value=95.0),
            operational_cost=DashboardKPI(label="Cost", value=50000),
            return_rate=DashboardKPI(label="Returns", value=5.0),
            active_customers=DashboardKPI(label="Customers", value=50),
            customer_satisfaction=DashboardKPI(label="CSAT", value=4.2),
        )
        assert dash.total_shipments.value == 1000

    def test_weekly_report(self):
        report = WeeklyReport(
            week="2026-W42",
            generated_at="2026-10-16T07:00Z",
            summary="Good week",
            highlights=["OT rate improved"],
            metrics={"shipments": 1200},
        )
        assert report.metrics["shipments"] == 1200