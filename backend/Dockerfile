# Отличие от шаблона: проект разрабатывается без uv (pip), поэтому uv.lock
# не генерируется — uv sync разрешает зависимости при сборке (без --frozen).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev --no-install-project

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
# пакет app лежит в src/ (макет шаблона) — добавляем в путь импорта
ENV PYTHONPATH=/app/src
COPY src ./src
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
