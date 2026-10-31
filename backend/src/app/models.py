"""ORM-модели платформы (этап E3).

Минимум для MVP: пользователь GitHub, прогресс по урокам, отметки задач
(autogress-подход к автопроверке — самопроверка + PR-ссылка; песочница — этап 2),
бейджи. Время — UTC (ISO-строки хранит SQLite как текст через DateTime).
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    """Ученик/наставник: минимум ПДн — только данные GitHub."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    login: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="student")  # student | mentor
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LessonProgress(Base):
    """Отметка «урок пройден» учеником."""

    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[str] = mapped_column(String(64), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TaskSubmission(Base):
    """Отметка задачи с автопроверкой (этап E4, self-check)."""

    __tablename__ = "task_submissions"
    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_user_task"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[str] = mapped_column(String(64))
    task_id: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(20), default="self_check")  # self_check | pyodide
    proof_url: Mapped[str] = mapped_column(String(500), default="")  # коммит/PR
    verdict: Mapped[str] = mapped_column(String(20), default="passed")  # passed | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Badge(Base):
    """Бейдж пролёта (Entry / Core / Pro)."""

    __tablename__ = "badges"
    __table_args__ = (UniqueConstraint("user_id", "badge", name="uq_user_badge"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    badge: Mapped[str] = mapped_column(String(20))  # entry | core | pro
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RouterResult(Base):
    """Результат роутера-диагностики (рекомендация пролёта)."""

    __tablename__ = "router_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recommended_level: Mapped[str] = mapped_column(String(4))  # L1 | L2 | L3
    answers: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


__all__ = [
    "Badge",
    "LessonProgress",
    "RouterResult",
    "TaskSubmission",
    "User",
    "utcnow",
]
