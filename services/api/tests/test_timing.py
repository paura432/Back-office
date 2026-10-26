import logging

from httpx import ASGITransport, AsyncClient

from main import app


async def test_http_timing_log_uses_route_template(caplog):
    caplog.set_level(logging.INFO, logger="trackflow.http")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert "http_request method=GET route=/health status_code=200 duration_ms=" in caplog.text
