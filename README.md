# track-platform — платформа трека «Python. Путь инженера»

MVP платформы: каталог уроков, прогресс ученика, автопроверка задач и
роутер-диагностика. Разработана на основе [`template-fullstack`](../template-fullstack/)
(шаблон не изменяется — проект развивается в своей директории).

Позиционирование — просветительская и справочная деятельность (мастер-план,
раздел 9): вход свободный, без зачисления; только терминология трека/пролёт/
урок/задача/бейдж/портфолио.

## Стек

- Backend: FastAPI, Pydantic v2, Uvicorn (pytest, ruff, mypy)
- Frontend: React 18, Vite, TypeScript strict, Vitest
- Инфраструктура: docker-compose, nginx; целевой хостинг — VPS (Linux + Docker)
- Аутентификация: GitHub OAuth (этап E3)
- Автопроверка: Pyodide в браузере (L1) + self-check с PR-ссылкой (L2/L3);
  интерфейс `CheckRunner` закладывает интеграцию Judge0/Piston (этап 2)

## Запуск

### Docker (полный стек)

```bash
cp .env.example .env      # при необходимости
docker compose up -d --build
# frontend: http://localhost:3001 (API проксируется на /api)
# API напрямую: http://localhost:8001/api/health
# Порты настраиваются: BACKEND_PORT / FRONTEND_PORT (в .env) — чтобы не
# конфликтовать с другими проектами на одной машине
```

### Локальная разработка

```bash
# Backend (:8000)
cd backend && uv sync && uv run make dev

# Frontend (:5173, прокси /api → localhost:8000)
cd frontend && npm ci && npm run dev
```

### Проверки

```bash
cd backend && uv run make check
cd frontend && npm run typecheck && npm test && npm run build
```

## Структура

```
├── docker-compose.yml       # backend + frontend
├── backend/                 # FastAPI (health; далее: lessons, progress, submissions)
│   ├── src/app/
│   ├── tests/
│   └── Dockerfile
├── frontend/                # React + Vite + TS
│   └── src/
└── content/                 # собранный контент уроков (JSON из curriculum/, этап E1)
```

## План разработки MVP

| Этап | Содержание                                                                                         | Статус                                          |
| ---- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| E0   | Каркас из шаблона, переименование, проверки                                                        | ✅                                              |
| E1   | Контент-пайплайн: `curriculum/*.md` (YAML-метаданные) → JSON-бандл                                 | ✅                                              |
| E2   | API каталога/уроков · UI каталога и страницы урока (hash-роутинг, markdown через marked+DOMPurify) | ✅                                              |
| E3   | GitHub OAuth + прогресс (сессии HMAC, БД)                                                          | ✅ (OAuth — нужны ключи для живого входа)       |
| E4   | Автопроверка: self-check + Pyodide-песочница L1 в браузере (WASM)                                  | ✅ (серверная песочница Judge0/Piston — этап 2) |
| E5   | Роутер-диагностика: анкета порога L2, рекомендация, сохранение                                     | ✅ (порог L3 — ревью наставника, вне MVP)       |
| E6   | Бейджи (авто-выдача по завершении пролёта) + страница портфолио                                    | ✅                                              |
| E7   | Деплой VPS (PostgreSQL, HTTPS, бэкапы)                                                             | ⬜                                              |

План целиком — в техническом решении MVP (см. историю трека); контент — в
[`../curriculum/`](../curriculum/README.md), эталон уроков — [`../plans/py-engineer-track/lesson-template.md`](../plans/py-engineer-track/lesson-template.md).

## Документация

- [`AGENTS.md`](AGENTS.md) — правила для ИИ-агентов (унаследованы из шаблона)
- [`TECHNICAL.md`](TECHNICAL.md) — архитектура и стек
- [`docs/constraints.md`](docs/constraints.md) — ограничения
- [`BACKLOG.md`](BACKLOG.md) — бэклог (источник истины)

## Лицензия

MIT
