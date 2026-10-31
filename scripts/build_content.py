"""Контент-пайплайн платформы: curriculum/*.md → content/content.json (этап E1).

Собирает уроки и обзоры модулей трека из Markdown-файлов с YAML-фронт-маттером
(шаблон урока: plans/py-engineer-track/lesson-template.md). Только stdlib;
парсер фронт-маттера рассчитан на простые ключи шаблона (скаляры и списки
в квадратных скобках).

Использование (из корня репозитория education):

    python platform/scripts/build_content.py

Результат: platform/content/content.json — idempotent (пересборка не меняет
существующие ключи уроков, id берётся из метаданных, а не из пути файла).
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # education/
CURRICULUM = ROOT / "curriculum"
# Контент бандлится вместе с приложением (уходит в docker-образ backend)
OUTPUT = Path(__file__).resolve().parents[1] / "backend" / "src" / "app" / "data" / "content.json"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LIST_RE = re.compile(r"^\[(.*)\]$")


def parse_front_matter(text: str) -> tuple[dict[str, object], str]:
    """Разобрать YAML-фронт-маттер (плоские ключи) и вернуть (метаданные, тело)."""
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, object] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        list_match = LIST_RE.match(value)
        if list_match:
            items = [item.strip().strip("'\"") for item in list_match.group(1).split(",") if item.strip()]
            meta[key.strip()] = items
        elif value in ("true", "false"):
            meta[key.strip()] = value == "true"
        elif re.fullmatch(r"\d+", value):
            meta[key.strip()] = int(value)
        else:
            meta[key.strip()] = value.strip("'\"")
    return meta, text[match.end():]


def parse_file(path: Path) -> dict[str, object] | None:
    """Разобрать один урок/обзор; None — если нет обязательных метаданных."""
    text = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    if "id" not in meta or "level" not in meta:
        return None
    kind = "lesson" if path.name.startswith("lesson-") else "module"
    return {
        "id": meta["id"],
        "kind": kind,
        "level": meta["level"],
        "module": meta.get("module", ""),
        "title": meta.get("title", ""),
        "prerequisites": meta.get("prerequisites", []),
        "skills": meta.get("skills", []),
        "time_est_min": meta.get("time_est_min", 0),
        "badge_related": meta.get("badge_related", False),
        "rel_path": path.relative_to(ROOT).as_posix(),
        "body": body.strip(),
    }


def build() -> dict[str, object]:
    items: list[dict[str, object]] = []
    for path in sorted(CURRICULUM.rglob("*.md")):
        parsed = parse_file(path)
        if parsed is not None:
            items.append(parsed)
    lessons = [item for item in items if item["kind"] == "lesson"]
    modules = [item for item in items if item["kind"] == "module"]
    return {
        "built_at": date.today().isoformat(),
        "levels": [
            {"level": level, "modules": sorted({str(i["module"]) for i in items if i["level"] == level})}
            for level in ("L1", "L2", "L3")
        ],
        "lessons": lessons,
        "modules": modules,
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    content = build()
    OUTPUT.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"content.json: {len(content['lessons'])} уроков, "
        f"{len(content['modules'])} модулей -> {OUTPUT}"
    )


if __name__ == "__main__":
    main()
