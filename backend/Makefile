.PHONY: install lint format typecheck test check dev

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy .

test:
	uv run pytest

check: lint typecheck test

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
