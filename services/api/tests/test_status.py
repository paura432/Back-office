from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.parametrize(
    ("database_available", "expected_status"),
    [(True, "operational"), (False, "degraded")],
)
async def test_status_endpoint_reports_database_state(database_available, expected_status):
    with patch("main.check_database", return_value=database_available) as check_database:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/status")

    assert response.status_code == 200
    assert response.json() == {"status": expected_status}
    check_database.assert_called_once_with()


async def test_status_never_discloses_database_details():
    sentinel = "postgresql://private-user:private-password@db/private-db"
    with patch("main.check_database", return_value=False):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/status")

    assert response.status_code == 200
    assert sentinel not in response.text
    assert "password" not in response.text.lower()


def test_status_has_explicit_openapi_response_model():
    operation = app.openapi()["paths"]["/status"]["get"]

    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/StatusResponse"
    }
    assert set(operation["responses"]) == {"200"}
