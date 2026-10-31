"""БД платформы (этап E3): движок, сессии, инициализация схемы.

MVP: SQLite по умолчанию, в проде DATABASE_URL → PostgreSQL.
Миграции (alembic) — этап после MVP: пока create_all при старте.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.models import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Ленивый движок по DATABASE_URL (создаётся один раз).

    Для in-memory SQLite (sqlite://) — StaticPool: одна общая связь,
    чтобы схема и данные были видны всем сессиям (используется в тестах).
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        if settings.database_url == "sqlite://":
            _engine = create_engine(
                "sqlite://",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            _engine = create_engine(
                settings.database_url,
                connect_args={"check_same_thread": False}
                if settings.database_url.startswith("sqlite")
                else {},
            )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Фабрика сессий (создаётся один раз)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def init_db() -> None:
    """Создать схему (MVP: create_all; миграции — после MVP)."""
    Base.metadata.create_all(get_engine())


def get_db() -> Iterator[Session]:
    """FastAPI-зависимость: сессия БД на запрос."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
