"""Тесты контент-эндпоинтов (этап E2)."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app import content
from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def test_content_bundle_loaded() -> None:
    """Бандл content.json читается и содержит три уровня трека."""
    data = content.load_content()
    assert [level["level"] for level in data["levels"]] == ["L1", "L2", "L3"]
    assert len(data["lessons"]) >= 17
    assert len(data["modules"]) >= 10


async def test_catalog(client: AsyncClient) -> None:
    """Каталог: уровни с модулями, без тел уроков."""
    response = await client.get("/api/v1/catalog")
    assert response.status_code == 200
    levels = response.json()
    assert [level["level"] for level in levels] == ["L1", "L2", "L3"]
    for level in levels:
        assert level["modules"], level
        for module in level["modules"]:
            assert "body" not in module


async def test_lessons_index(client: AsyncClient) -> None:
    """Список уроков без тел."""
    response = await client.get("/api/v1/lessons")
    assert response.status_code == 200
    lessons = response.json()
    ids = {lesson["id"] for lesson in lessons}
    assert "lesson-L2-M1-01" in ids
    for lesson in lessons:
        assert "body" not in lesson


async def test_lesson_by_id_returns_body(client: AsyncClient) -> None:
    """Полный урок содержит markdown-тело и метаданные."""
    response = await client.get("/api/v1/lessons/lesson-L2-M1-01")
    assert response.status_code == 200
    lesson = response.json()
    assert lesson["title"]
    assert "create_default" in lesson["body"]


async def test_lesson_not_found(client: AsyncClient) -> None:
    """Несуществующий урок → 404."""
    response = await client.get("/api/v1/lessons/lesson-NOPE")
    assert response.status_code == 404


async def test_module_overview_by_id(client: AsyncClient) -> None:
    """Обзор модуля (module-overview) доступен целиком, с телом."""
    data = content.load_content()
    module_id = str(data["modules"][0]["id"])
    response = await client.get(f"/api/v1/modules/{module_id}")
    assert response.status_code == 200
    module = response.json()
    assert module["id"] == module_id
    assert module["title"]
    assert module["body"]


async def test_module_not_found(client: AsyncClient) -> None:
    """Несуществующий модуль → 404."""
    response = await client.get("/api/v1/modules/module-NOPE")
    assert response.status_code == 404
