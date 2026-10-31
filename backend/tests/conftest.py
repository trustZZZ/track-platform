"""Общие фикстуры тестов платформы.

БД — in-memory SQLite (StaticPool, общая связь): настроек меняем database_url
до создания приложения; схему создаёт init_db() внутри create_app.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Тест-клиент на in-memory БД."""
    get_settings().database_url = "sqlite://"
    with TestClient(create_app()) as test_client:
        yield test_client
