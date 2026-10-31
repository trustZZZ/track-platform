"""Роутер-диагностика (этап E5): задачи порога L2 и рекомендация пролёта.

По мастер-плану (раздел 5): вход в L1 свободный; порог в L2 — задачи
«периметр треугольника», условия, циклы с автопроверкой; порог в L3 —
мини-проект + критерии качества (ручное ревью наставника, вне MVP).
Результат роутера — рекомендация; выбор остаётся за учеником.
"""
from __future__ import annotations

from typing import Any

# Задачи порога L2 (детерминированные ответы — авто-проверка без песочницы).
# answers НЕ отдаются клиенту (GET /router/tasks возвращает задачи без них).
TASKS: list[dict[str, Any]] = [
    {
        "task_id": "perimeter",
        "topic": "функции и арифметика",
        "question": (
            "Периметр треугольника со сторонами a, b, c — сумма сторон. "
            "Чему равен периметр треугольника 3, 4, 5?"
        ),
        "answer": 12,
    },
    {
        "task_id": "conditions",
        "topic": "условия",
        "question": (
            "Код: x = 0; if 5 > 3: x = 10; else: x = 20. "
            "Какое значение окажется в x?"
        ),
        "answer": 10,
    },
    {
        "task_id": "loops",
        "topic": "циклы",
        "question": "Код: s = 0; for i in range(1, 11): s += i. Чему равно s? (сумма 1..10)",
        "answer": 55,
    },
]

# Правила рекомендации (мастер-план, раздел 5)
RULES: dict[str, dict[str, str]] = {
    "L1": {
        "level": "L1",
        "bridge": "B1",
        "text": "Рекомендуем начать с пролёта Entry (L1): база Python — переменные, условия, циклы.",
    },
    "L2_B1": {
        "level": "L2",
        "bridge": "B1",
        "text": "Рекомендуем пролёт Core (L2), но сначала мост B1 — доводка условий и циклов.",
    },
    "L2": {
        "level": "L2",
        "bridge": "",
        "text": "Рекомендуем пролёт Core (L2) — «конструктор» на проекте 3D-race.",
    },
    "L3": {
        "level": "L3",
        "bridge": "B2",
        "text": "Задачи порога L2 решены свободно: можно претендовать на Pro (L3) — потребуются мини-проект и ревью качества (мост B2).",
    },
}


def router_tasks() -> list[dict[str, Any]]:
    """Задачи анкеты БЕЗ ответов (для клиента)."""
    return [
        {"task_id": task["task_id"], "topic": task["topic"], "question": task["question"]}
        for task in TASKS
    ]


def recommend(answers: list[dict[str, Any]]) -> dict[str, Any]:
    """Проверить ответы и вернуть рекомендацию (score, уровень, мост, текст)."""
    by_id = {task["task_id"]: task for task in TASKS}
    score = 0
    details: list[dict[str, Any]] = []
    for item in answers:
        task = by_id.get(str(item.get("task_id", "")))
        if task is None:
            continue
        raw_value: Any = item.get("value")
        try:
            value = float(str(raw_value))
        except (TypeError, ValueError):
            value = None
        correct = value is not None and abs(value - float(task["answer"])) < 1e-9
        if correct:
            score += 1
        details.append({"task_id": task["task_id"], "correct": correct})

    total = len(TASKS)
    if score == total:
        key = "L3"  # свободно решён весь порог → разговор о L3 через B2
    elif score >= 2:
        key = "L2_B1"
    else:
        key = "L1"
    rule = RULES[key]
    return {
        "score": score,
        "total": total,
        "recommended_level": rule["level"],
        "bridge": rule["bridge"],
        "text": rule["text"],
        "details": details,
    }
