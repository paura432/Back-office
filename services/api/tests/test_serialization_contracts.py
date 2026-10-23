from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.schemas.auth import UserProfileResponse
from main import app


async def test_every_application_route_declares_a_pydantic_response_model():
    routes = [route for route in app.routes if isinstance(route, APIRoute)]

    assert len(routes) == 32
    assert all(route.response_model is not None for route in routes)
    assert all(
        route.response_field is not None
        for route in routes
    )


def test_openapi_documents_health_status_and_application_routes():
    schema = app.openapi()

    assert schema["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    assert schema["paths"]["/status"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/StatusResponse"
    }
    for route in (route for route in app.routes if isinstance(route, APIRoute)):
        for method in route.methods or ():
            operation = schema["paths"][route.path][method.lower()]
            assert "200" in operation["responses"] or "201" in operation["responses"]


async def test_http_response_model_filters_sensitive_and_uncontracted_fields():
    test_app = FastAPI()

    @test_app.get("/profile", response_model=UserProfileResponse)
    def profile_fixture():
        return {
            "id": 17,
            "email": "ops@example.test",
            "full_name": "Operations User",
            "is_active": True,
            "password": "DO_NOT_EXPOSE_PASSWORD",
            "password_hash": "DO_NOT_EXPOSE_HASH",
            "salt": "DO_NOT_EXPOSE_SALT",
            "reset_token": "DO_NOT_EXPOSE_RESET_TOKEN",
            "internal_metadata": {"role_source": "private"},
        }

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/profile")

    assert response.status_code == 200
    assert response.json() == {
        "id": 17,
        "email": "ops@example.test",
        "full_name": "Operations User",
        "is_active": True,
    }
    for secret in (
        "DO_NOT_EXPOSE_PASSWORD",
        "DO_NOT_EXPOSE_HASH",
        "DO_NOT_EXPOSE_SALT",
        "DO_NOT_EXPOSE_RESET_TOKEN",
        "internal_metadata",
    ):
        assert secret not in response.text
