"""Конфигурация backend (pydantic-settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "track-platform"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000

    # БД: SQLite по умолчанию (MVP); в проде — postgresql+psycopg://...
    database_url: str = "sqlite:///./track-platform.db"

    # GitHub OAuth (этап E3): без настроенных ключей auth-эндпоинты отвечают 503.
    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/api/v1/auth/github/callback"

    # Секрет подписи сессий (HMAC). В проде задавать через окружение!
    session_secret: str = "dev-insecure-secret"


@lru_cache
def get_settings() -> Settings:
    return Settings()
