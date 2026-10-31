"""Тесты аутентификации и прогресса (этап E3)."""

import itertools
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.core.config import get_settings
from app.db import get_session_factory
from app.models import User


@pytest.fixture
def github_configured() -> Iterator[None]:
    """Временно «настроенный» OAuth (без реального GitHub)."""
    settings = get_settings()
    saved = (settings.github_client_id, settings.github_client_secret)
    settings.github_client_id = "test-id"
    settings.github_client_secret = "test-secret"
    yield
    settings.github_client_id, settings.github_client_secret = saved


_unique_github_id = itertools.count(100)


@pytest.fixture
def logged_in_cookie(client: TestClient) -> Iterator[dict[str, str]]:
    """Создать (или найти) пользователя и вернуть cookie сессии.

    get-or-create: in-memory БД живёт весь процесс — идемпотентно к повторам.
    """
    db = get_session_factory()()
    github_id = next(_unique_github_id)
    user = db.query(User).filter(User.github_id == github_id).one_or_none()
    if user is None:
        user = User(github_id=github_id, login="tester")
        db.add(user)
        db.commit()
    cookie = {auth.SESSION_COOKIE: auth.create_session_token(user.id)}
    db.close()
    yield cookie


# ---------------------------------------------------------------------------
# Аутентификация
# ---------------------------------------------------------------------------

def test_auth_url_503_when_not_configured(client: TestClient) -> None:
    """Без ключей OAuth auth-эндпоинты отвечают 503 (контент доступен и так)."""
    response = client.get("/api/v1/auth/github/url")
    assert response.status_code == 503


def test_auth_url_when_configured(client: TestClient, github_configured: None) -> None:
    """С настроенными ключами возвращается authorize_url с read:user."""
    response = client.get("/api/v1/auth/github/url")
    assert response.status_code == 200
    url = response.json()["authorize_url"]
    assert "github.com/login/oauth/authorize" in url
    assert "scope=read%3Auser" in url or "scope=read:user" in url


def test_callback_flow(
    client: TestClient,
    github_configured: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Callback: обмен кода (замокан) → upsert → cookie сессии."""

    def fake_exchange(code: str) -> str:
        assert code == "the-code"
        return "token-123"

    def fake_fetch(token: str) -> dict[str, Any]:
        return {"id": 7, "login": "octocat"}

    monkeypatch.setattr(auth, "exchange_code", fake_exchange)
    monkeypatch.setattr(auth, "fetch_github_user", fake_fetch)

    response = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "the-code"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert auth.SESSION_COOKIE in response.cookies

    me = client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["login"] == "octocat"


def test_me_unauthorized(client: TestClient) -> None:
    """Без сессии /me → 401 (контент — открыт, прогресс — нет)."""
    assert client.get("/api/v1/me").status_code == 401


def test_session_tamper_rejected(client: TestClient, logged_in_cookie: dict[str, str]) -> None:
    """Подделанная подпись сессии → 401."""
    cookie = logged_in_cookie[auth.SESSION_COOKIE]
    tampered = cookie[:-4] + "0000"
    response = client.get("/api/v1/me", cookies={auth.SESSION_COOKIE: tampered})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Прогресс
# ---------------------------------------------------------------------------

def test_complete_lesson(client: TestClient, logged_in_cookie: dict[str, str]) -> None:
    """Отметка урока пройденным + повторная отметка идемпотентна."""
    cookies = logged_in_cookie
    first = client.post("/api/v1/progress/lesson-L2-M1-01/complete", cookies=cookies)
    assert first.status_code == 200
    again = client.post("/api/v1/progress/lesson-L2-M1-01/complete", cookies=cookies)
    assert again.status_code == 200
    me = client.get("/api/v1/me", cookies=cookies).json()
    assert me["completed_lessons"] == ["lesson-L2-M1-01"]


def test_complete_unknown_lesson_404(
    client: TestClient, logged_in_cookie: dict[str, str]
) -> None:
    """Прогресс можно отмечать только для существующих уроков."""
    response = client.post("/api/v1/progress/lesson-NOPE/complete", cookies=logged_in_cookie)
    assert response.status_code == 404


def test_submit_task_self_check(
    client: TestClient, logged_in_cookie: dict[str, str]
) -> None:
    """Self-check отметка задачи: обязательна ссылка на доказательство."""
    cookies = logged_in_cookie
    bad = client.post(
        "/api/v1/submissions",
        json={"lesson_id": "lesson-L2-M1-01", "task_id": "t1", "proof_url": "не ссылка"},
        cookies=cookies,
    )
    assert bad.status_code == 422

    ok = client.post(
        "/api/v1/submissions",
        json={
            "lesson_id": "lesson-L2-M1-01",
            "task_id": "t1",
            "proof_url": "https://github.com/tester/l2-core/pull/1",
        },
        cookies=cookies,
    )
    assert ok.status_code == 200
    me = client.get("/api/v1/me", cookies=cookies).json()
    assert me["tasks"][0]["task_id"] == "t1"
    assert me["tasks"][0]["verdict"] == "passed"


def test_submit_task_pyodide_without_url(
    client: TestClient, logged_in_cookie: dict[str, str]
) -> None:
    """Pyodide-задача (E4): выполнена в браузере — ссылка не нужна."""
    cookies = logged_in_cookie
    response = client.post(
        "/api/v1/submissions",
        json={
            "lesson_id": "lesson-L2-M1-01",
            "task_id": "lesson-L2-M1-01:sandbox",
            "kind": "pyodide",
        },
        cookies=cookies,
    )
    assert response.status_code == 200

    wrong_kind = client.post(
        "/api/v1/submissions",
        json={"lesson_id": "lesson-L2-M1-01", "task_id": "t2", "kind": "judge0"},
        cookies=cookies,
    )
    assert wrong_kind.status_code == 422


# ---------------------------------------------------------------------------
# Роутер-диагностика (E5)
# ---------------------------------------------------------------------------

def test_router_tasks_no_answers(client: TestClient) -> None:
    """Анкета отдаётся без ответов (они только на сервере)."""
    response = client.get("/api/v1/router/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert [task["task_id"] for task in tasks] == ["perimeter", "conditions", "loops"]
    assert all("answer" not in task for task in tasks)


def test_router_full_score_recommends_l3_bridge(
    client: TestClient, logged_in_cookie: dict[str, str]
) -> None:
    """3/3 → разговор о L3 (мост B2); результат сохраняется для вошедшего."""
    response = client.post(
        "/api/v1/router",
        json={
            "answers": [
                {"task_id": "perimeter", "value": 12},
                {"task_id": "conditions", "value": 10},
                {"task_id": "loops", "value": 55},
            ]
        },
        cookies=logged_in_cookie,
    )
    assert response.status_code == 200
    result = response.json()
    assert result["score"] == 3
    assert result["recommended_level"] == "L3"
    assert result["bridge"] == "B2"
    assert result["saved"] is True


def test_router_partial_score_recommends_l2_b1(client: TestClient) -> None:
    """2/3 → L2 с мостом B1; анониму результат не сохраняется."""
    response = client.post(
        "/api/v1/router",
        json={
            "answers": [
                {"task_id": "perimeter", "value": 12},
                {"task_id": "conditions", "value": 999},
                {"task_id": "loops", "value": 55},
            ]
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["recommended_level"] == "L2"
    assert result["bridge"] == "B1"
    assert result["saved"] is False


def test_router_low_score_recommends_l1(client: TestClient) -> None:
    """0/3 → L1 (вход свободный)."""
    response = client.post(
        "/api/v1/router",
        json={"answers": [{"task_id": "perimeter", "value": "abc"}]},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["score"] == 0
    assert result["recommended_level"] == "L1"


def test_router_invalid_payload(client: TestClient) -> None:
    """Без списка answers → 422."""
    assert client.post("/api/v1/router", json={"answers": "nope"}).status_code == 422


# ---------------------------------------------------------------------------
# Бейджи и портфолио (E6)
# ---------------------------------------------------------------------------

def _complete_all_l2(client: TestClient, cookies: dict[str, str]) -> None:
    """Пройти все уроки L2 из контента (для бейджа core)."""
    from app.content import load_content

    for lesson in load_content()["lessons"]:
        if lesson["level"] == "L2":
            response = client.post(
                f"/api/v1/progress/{lesson['id']}/complete", cookies=cookies
            )
            assert response.status_code == 200


def test_badge_core_after_all_l2_lessons(
    client: TestClient, logged_in_cookie: dict[str, str]
) -> None:
    """Пройдены все уроки L2 → выдаётся бейдж core (автоматом и по claim)."""
    cookies = logged_in_cookie
    _complete_all_l2(client, cookies)

    # Автовыдача при завершающем отмечании уже сработала; claim идемпотентен.
    claim = client.post("/api/v1/badges/claim", cookies=cookies)
    assert claim.status_code == 200
    assert "core" in claim.json()["badges"]
    assert claim.json()["granted"] == []  # уже выдан автоматом

    portfolio = client.get("/api/v1/portfolio", cookies=cookies).json()
    assert "core" in portfolio["badges"]
    l2 = next(level for level in portfolio["levels"] if level["level"] == "L2")
    assert l2["done"] == l2["total"]
    assert portfolio["github_url"] == "https://github.com/tester"


def test_portfolio_requires_auth(client: TestClient) -> None:
    """Портфолио — только для вошедших (ссылка на GitHub — личные данные)."""
    assert client.get("/api/v1/portfolio").status_code == 401


def test_badge_not_granted_early(
    client: TestClient, logged_in_cookie: dict[str, str]
) -> None:
    """Один пройденный урок — бейджа ещё нет."""
    cookies = logged_in_cookie
    client.post("/api/v1/progress/lesson-L2-M1-01/complete", cookies=cookies)
    claim = client.post("/api/v1/badges/claim", cookies=cookies)
    assert claim.json()["granted"] == []
    assert "core" not in claim.json()["badges"]
    me = client.get("/api/v1/me", cookies=cookies).json()
    assert me["badges"] == []
