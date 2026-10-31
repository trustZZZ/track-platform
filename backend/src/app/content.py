"""Загрузчик контента уроков (этап E1: curriculum → content.json → API).

content.json собирается скриптом scripts/build_content.py и бандлится вместе
с приложением (src/app/data/content.json). Файл — read-only данные: anyio
кэширует разбор в памяти.
"""
from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast


def _content_path() -> Any:
    """Путь к бандл-файлу content.json внутри пакета app."""
    return files("app").joinpath("data", "content.json")


@lru_cache(maxsize=1)
def load_content() -> dict[str, Any]:
    """Прочитать и разобрать content.json (кэшируется на процесс)."""
    raw: bytes = _content_path().read_bytes()
    data: dict[str, Any] = json.loads(raw)
    return data


def catalog() -> list[dict[str, Any]]:
    """Каталог: уровни и их модули (без тел уроков).

    Модули собираются из обзоров module-overview (если есть) и выводятся
    из уроков (L2 не имеет обзоров — модуль = группа уроков).
    """
    content = load_content()
    result: list[dict[str, Any]] = []
    for level in content["levels"]:
        level_key = str(level["level"])
        by_module: dict[str, dict[str, Any]] = {}
        for module in content["modules"]:
            if module["level"] == level_key:
                by_module[str(module["module"])] = {
                    "id": module["id"],
                    "module": module["module"],
                    "title": module["title"],
                    "time_est_min": module["time_est_min"],
                    "rel_path": module["rel_path"],
                    "lessons": 0,
                }
        for lesson in content["lessons"]:
            if lesson["level"] == level_key:
                module_key = str(lesson["module"])
                entry = by_module.setdefault(
                    module_key,
                    {"id": None, "module": module_key, "title": "", "time_est_min": 0, "rel_path": None, "lessons": 0},
                )
                entry["lessons"] = int(entry["lessons"]) + 1
                if not entry["title"]:
                    entry["title"] = lesson["title"]
                if entry["id"] is None:
                    entry["time_est_min"] = int(entry["time_est_min"]) + int(lesson["time_est_min"])
        result.append({"level": level_key, "modules": list(by_module.values())})
    return result


def lessons_index() -> list[dict[str, Any]]:
    """Список уроков без тел (для каталога)."""
    return [
        {
            "id": lesson["id"],
            "level": lesson["level"],
            "module": lesson["module"],
            "title": lesson["title"],
            "time_est_min": lesson["time_est_min"],
            "skills": lesson["skills"],
        }
        for lesson in load_content()["lessons"]
    ]


def lesson_by_id(lesson_id: str) -> dict[str, Any] | None:
    """Урок целиком (с телом markdown) по id; None — не найден."""
    found = next(
        (lesson for lesson in load_content()["lessons"] if lesson["id"] == lesson_id),
        None,
    )
    return cast("dict[str, Any] | None", found)


def module_by_id(module_id: str) -> dict[str, Any] | None:
    """Обзор модуля целиком (с телом) по id; None — не найден или обзора нет."""
    found = next(
        (module for module in load_content()["modules"] if module["id"] == module_id),
        None,
    )
    return cast("dict[str, Any] | None", found)
