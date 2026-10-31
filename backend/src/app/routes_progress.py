"""Роуты прогресса (этапы E3/E4): профиль, отметки уроков и задач, бейджи.

Требуют сессию (cookie). Отметка задачи — self-check: ученик прикладывает
ссылку на коммит/PR; серверная песочница — этап 2 (CheckRunner-интерфейс).
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth, router_tasks
from app.content import lesson_by_id, load_content
from app.db import get_db
from app.models import Badge, LessonProgress, RouterResult, TaskSubmission, User

router = APIRouter(prefix="/api/v1", tags=["progress"])


def get_current_user(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> User:
    """Зависимость: пользователь по сессионной cookie; 401 без валидной сессии."""
    token = request.cookies.get(auth.SESSION_COOKIE, "")
    user_id = auth.verify_session_token(token) if token else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Требуется вход через GitHub")
    user = auth.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Сессия недействительна")
    return user


@router.get("/me")
async def me(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Профиль + сводка прогресса (пройденные уроки, задачи, бейджи)."""
    lessons = db.execute(
        select(LessonProgress).where(LessonProgress.user_id == user.id)
    ).scalars().all()
    tasks = db.execute(
        select(TaskSubmission).where(TaskSubmission.user_id == user.id)
    ).scalars().all()
    badges = db.execute(select(Badge).where(Badge.user_id == user.id)).scalars().all()
    return {
        "id": user.id,
        "login": user.login,
        "role": user.role,
        "completed_lessons": sorted(item.lesson_id for item in lessons),
        "tasks": [
            {"task_id": item.task_id, "lesson_id": item.lesson_id, "verdict": item.verdict}
            for item in tasks
        ],
        "badges": sorted(item.badge for item in badges),
    }


def _level_lesson_ids(level: str) -> set[str]:
    """Все id уроков уровня из контента."""
    return {
        str(lesson["id"])
        for lesson in load_content()["lessons"]
        if lesson["level"] == level
    }


def _completed_lesson_ids(db: Session, user: User) -> set[str]:
    """Пройденные уроки ученика."""
    return {
        item.lesson_id
        for item in db.execute(
            select(LessonProgress).where(LessonProgress.user_id == user.id)
        ).scalars().all()
    }


def _existing_badges(db: Session, user: User) -> set[str]:
    """Уже выданные бейджи."""
    return {
        item.badge
        for item in db.execute(
            select(Badge).where(Badge.user_id == user.id)
        ).scalars().all()
    }


def _grant_badges(db: Session, user: User) -> list[str]:
    """Выдать заслуженные бейджи (этап E6).

    Условие бейджа уровня: пройдены ВСЕ уроки этого уровня из контента
    (entry=L1, core=L2, pro=L3). Идемпотентно (unique user+badge);
    возвращает только новые бейджи.
    """
    completed = _completed_lesson_ids(db, user)
    existing = _existing_badges(db, user)
    mapping = {"L1": "entry", "L2": "core", "L3": "pro"}
    granted: list[str] = []
    for level, badge in mapping.items():
        lesson_ids = _level_lesson_ids(level)
        if lesson_ids and lesson_ids <= completed and badge not in existing:
            db.add(Badge(user_id=user.id, badge=badge))
            granted.append(badge)
    if granted:
        db.commit()
    return granted


def _portfolio(db: Session, user: User) -> dict[str, Any]:
    """Сводка портфолио: прогресс по пролётам + бейджи + ссылка на GitHub."""
    levels = []
    completed = _completed_lesson_ids(db, user)
    for level in ("L1", "L2", "L3"):
        lesson_ids = _level_lesson_ids(level)
        levels.append(
            {
                "level": level,
                "done": len(lesson_ids & completed),
                "total": len(lesson_ids),
            }
        )
    return {
        "login": user.login,
        "github_url": f"https://github.com/{user.login}",
        "levels": levels,
        "badges": sorted(_existing_badges(db, user)),
    }


@router.get("/portfolio")
async def portfolio(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Портфолио ученика: прогресс по пролётам, бейджи, GitHub-ссылка."""
    return _portfolio(db, user)


@router.post("/badges/claim")
async def claim_badges(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Проверить условия и выдать заслуженные бейджи (идемпотентно)."""
    granted = _grant_badges(db, user)
    return {"granted": granted, "badges": sorted(_existing_badges(db, user))}


@router.post("/progress/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Отметить урок пройденным (id должен существовать в контенте)."""
    if lesson_by_id(lesson_id) is None:
        raise HTTPException(status_code=404, detail=f"Урок не найден: {lesson_id}")
    exists = db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson_id
        )
    ).scalar_one_or_none()
    new_badges: list[str] = []
    if exists is None:
        db.add(LessonProgress(user_id=user.id, lesson_id=lesson_id))
        db.commit()
        new_badges = _grant_badges(db, user)
    return {"lesson_id": lesson_id, "completed": True, "new_badges": new_badges}


@router.post("/submissions")
async def submit_task(
    payload: dict[str, Any],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Отметить задачу (этап E4, CheckRunner MVP).

    kind="self_check" (по умолчанию): proof_url обязателен (коммит/PR).
    kind="pyodide": задача выполнена в браузерной песочнице — ссылка не нужна.
    Серверная песочница (Judge0/Piston) — этап 2, интерфейс не меняется.
    """
    lesson_id = str(payload.get("lesson_id", ""))
    task_id = str(payload.get("task_id", ""))
    proof_url = str(payload.get("proof_url", "")).strip()
    kind = str(payload.get("kind", "self_check"))
    if kind not in ("self_check", "pyodide"):
        raise HTTPException(status_code=422, detail="kind: self_check | pyodide")
    if not lesson_id or not task_id:
        raise HTTPException(status_code=422, detail="Нужны lesson_id и task_id")
    if lesson_by_id(lesson_id) is None:
        raise HTTPException(status_code=404, detail=f"Урок не найден: {lesson_id}")
    if kind == "self_check" and not proof_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=422, detail="для self_check нужен proof_url (коммит/PR)"
        )
    exists = db.execute(
        select(TaskSubmission).where(
            TaskSubmission.user_id == user.id, TaskSubmission.task_id == task_id
        )
    ).scalar_one_or_none()
    if exists is None:
        db.add(
            TaskSubmission(
                user_id=user.id,
                lesson_id=lesson_id,
                task_id=task_id,
                kind=kind,
                proof_url=proof_url,
            )
        )
        db.commit()
    return {"task_id": task_id, "verdict": "passed"}


@router.get("/router/tasks")
async def router_tasks_list() -> list[dict[str, Any]]:
    """Задачи порога L2 (без ответов) — анкета роутера."""
    return router_tasks.router_tasks()


@router.post("/router")
async def router_submit(
    payload: dict[str, Any],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Проверить анкету роутера; для вошедших — сохранить рекомендацию."""
    answers_raw = payload.get("answers")
    if not isinstance(answers_raw, list):
        raise HTTPException(status_code=422, detail="answers должен быть списком")
    result = router_tasks.recommend(answers_raw)

    # Сохраняем только для вошедших (вход свободный — аноним тоже может пройти)
    token = request.cookies.get(auth.SESSION_COOKIE, "")
    user_id = auth.verify_session_token(token) if token else None
    if user_id is not None:
        db.add(
            RouterResult(
                user_id=user_id,
                recommended_level=str(result["recommended_level"]),
                answers=str(result["details"]),
            )
        )
        db.commit()
        result["saved"] = True
    else:
        result["saved"] = False
    return result
