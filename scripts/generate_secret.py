"""Генератор SESSION_SECRET для платформы (только stdlib).

Использование:

    python platform/scripts/generate_secret.py            # напечатать новый секрет
    python platform/scripts/generate_secret.py --env      # создать/дополнить platform/.env

Секрет подписывает сессии (HMAC, app/auth.py). Ротация секента вылогинивает
всех пользователей — меняйте только при компрометации.
"""
from __future__ import annotations

import argparse
import secrets
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = PLATFORM_DIR / ".env"


def generate_secret() -> str:
    """Криптостойкий секрет (32 байта энтропии, URL-safe)."""
    return secrets.token_urlsafe(32)


def append_to_env(secret: str) -> str:
    """Добавить SESSION_SECRET в platform/.env (не перезаписывая существующий)."""
    if ENV_PATH.exists():
        content = ENV_PATH.read_text(encoding="utf-8")
        if "SESSION_SECRET=" in content:
            return f"{ENV_PATH}: SESSION_SECRET уже задан — не менял"
        content = content.rstrip() + f"\nSESSION_SECRET={secret}\n"
    else:
        content = f"SESSION_SECRET={secret}\n"
    ENV_PATH.write_text(content, encoding="utf-8")
    return f"{ENV_PATH}: SESSION_SECRET добавлен"


def main() -> None:
    parser = argparse.ArgumentParser(description="Генератор SESSION_SECRET")
    parser.add_argument("--env", action="store_true", help="записать в platform/.env")
    args = parser.parse_args()

    secret = generate_secret()
    if args.env:
        print(append_to_env(secret))
    else:
        print(secret)


if __name__ == "__main__":
    main()
