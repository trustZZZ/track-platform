"""Роуты аутентификации (этап E3): GitHub OAuth + выход."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app import auth
from app.core.config import get_settings
from app.db import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/github/url")
async def github_url() -> dict[str, Any]:
    """Ссылка на согласие GitHub; 503, если OAuth не настроен."""
    if not auth.is_github_configured():
        raise HTTPException(
            status_code=503,
            detail="GitHub OAuth не настроен: задайте GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET",
        )
    return {"authorize_url": auth.build_authorize_url()}


@router.get("/github/callback")
async def github_callback(
    code: str, db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Обмен кода на токен → upsert пользователя → сессионная cookie."""
    if not auth.is_github_configured():
        raise HTTPException(status_code=503, detail="GitHub OAuth не настроен")
    access_token = auth.exchange_code(code)
    profile = auth.fetch_github_user(access_token)
    user = auth.upsert_user(db, int(profile["id"]), str(profile.get("login", "")))
    settings = get_settings()
    response = Response(status_code=302)
    response.headers["Location"] = "/"
    response.set_cookie(
        auth.SESSION_COOKIE,
        auth.create_session_token(user.id),
        httponly=True,
        samesite="lax",
        max_age=auth.SESSION_TTL_SECONDS,
        secure=settings.github_oauth_redirect_uri.startswith("https"),
    )
    return response


@router.post("/logout")
async def logout(request: Request) -> Response:
    """Выход: снять сессионную cookie."""
    response = Response(status_code=204)
    if request.cookies.get(auth.SESSION_COOKIE):
        response.delete_cookie(auth.SESSION_COOKIE)
    return response
