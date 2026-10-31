"""Точка входа FastAPI-приложения (платформа трека)."""

from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException

from app import content
from app.core.config import get_settings
from app.db import init_db
from app.routes_auth import router as auth_router
from app.routes_progress import router as progress_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Платформа трека «Python. Путь инженера»: уроки, прогресс, автопроверка.",
    )

    router = APIRouter(prefix="/api")

    router.add_api_route("/health", _health, methods=["GET"], tags=["health"])
    router.add_api_route("/v1/echo", _echo, methods=["POST"], tags=["echo"])
    router.add_api_route("/v1/catalog", _catalog, methods=["GET"], tags=["content"])
    router.add_api_route("/v1/lessons", _lessons, methods=["GET"], tags=["content"])
    router.add_api_route("/v1/lessons/{lesson_id}", _lesson, methods=["GET"], tags=["content"])
    router.add_api_route("/v1/modules/{module_id}", _module, methods=["GET"], tags=["content"])

    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(progress_router)

    init_db()
    return app


async def _health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


async def _echo(payload: dict[str, Any]) -> dict[str, Any]:
    """Пример контракта: возвращает входной объект как есть."""
    return {"echo": payload}


async def _catalog() -> list[dict[str, Any]]:
    """Каталог трека: уровни и модули (без тел уроков)."""
    return content.catalog()


async def _lessons() -> list[dict[str, Any]]:
    """Список уроков без тел (для каталога)."""
    return content.lessons_index()


async def _lesson(lesson_id: str) -> dict[str, Any]:
    """Урок целиком (с телом markdown)."""
    lesson = content.lesson_by_id(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Урок не найден: {lesson_id}")
    return lesson


async def _module(module_id: str) -> dict[str, Any]:
    """Обзор модуля (с телом markdown)."""
    module = content.module_by_id(module_id)
    if module is None:
        raise HTTPException(status_code=404, detail=f"Модуль не найден: {module_id}")
    return module


app = create_app()
