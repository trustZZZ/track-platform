"""Тесты API backend."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_echo(client: AsyncClient) -> None:
    response = await client.post("/api/v1/echo", json={"key": "value"})
    assert response.status_code == 200
    assert response.json()["echo"] == {"key": "value"}
