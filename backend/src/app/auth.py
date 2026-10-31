"""GitHub OAuth + сессии (этап E3).

Поток: GET /auth/github/url → authorize_url → GitHub → callback → обмен кода
на токен → данные пользователя → upsert в БД → HMAC-подписанная сессия в cookie.

Без настроенных github_client_id/secret эндпоинты отвечают 503 (MVP не требует
OAuth для чтения контента). Тестируемость: обмен кода вынесен в функции, которые
подменяются в тестах (не дёргаем GitHub из юнит-тестов).
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import User

SESSION_COOKIE = "tp_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_API = "https://api.github.com/user"


def is_github_configured() -> bool:
    """OAuth доступен только при заполненных ключах (env/.env)."""
    settings = get_settings()
    return bool(settings.github_client_id and settings.github_client_secret)


def build_authorize_url(state: str = "") -> str:
    """Ссылка на согласие GitHub (scope read:user — только публичный профиль)."""
    settings = get_settings()
    query = httpx.QueryParams(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_oauth_redirect_uri,
            "scope": "read:user",
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def exchange_code(code: str) -> str:
    """Обменять authorization_code на access_token (реальный HTTP-вызов)."""
    settings = get_settings()
    response = httpx.post(
        TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": settings.github_oauth_redirect_uri,
        },
        timeout=15,
    )
    response.raise_for_status()
    token: str = response.json().get("access_token", "")
    if not token:
        raise ValueError("GitHub не вернул access_token")
    return token


def fetch_github_user(access_token: str) -> dict[str, Any]:
    """Публичный профиль GitHub (id, login) по access_token."""
    response = httpx.get(
        USER_API,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def upsert_user(db: Session, github_id: int, login: str) -> User:
    """Найти или создать пользователя по github_id."""
    user = db.execute(select(User).where(User.github_id == github_id)).scalar_one_or_none()
    if user is None:
        user = User(github_id=github_id, login=login)
        db.add(user)
    else:
        user.login = login
    db.commit()
    return user


def _sign(payload: str) -> str:
    secret = get_settings().session_secret
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_token(user_id: int) -> str:
    """HMAC-подписанная сессия: '<user_id>.< issued_at >.<подпись>'."""
    issued = str(int(time.time()))
    payload = f"{user_id}.{issued}"
    return f"{payload}.{_sign(payload)}"


def verify_session_token(token: str) -> int | None:
    """Проверить подпись и срок; вернуть user_id или None."""
    try:
        user_id_raw, issued_raw, signature = token.split(".")
        payload = f"{user_id_raw}.{issued_raw}"
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        if time.time() - int(issued_raw) > SESSION_TTL_SECONDS:
            return None
        return int(user_id_raw)
    except (ValueError, TypeError):
        return None


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
