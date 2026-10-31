# TECHNICAL.md — Техническое описание (template-fullstack)

Источник истины об архитектуре fullstack-шаблона.

## 1. Назначение

Шаблон веб-приложения «под ключ»: FastAPI-бэкенд, React-фронтенд и
docker-compose для локального запуска всей связки.

## 2. Стек и версии

| Компонент         | Диапазон                   | Назначение                   |
| ----------------- | -------------------------- | ---------------------------- |
| Python            | >=3.12                     | backend                      |
| fastapi / uvicorn | >=0.115,<1.0 / >=0.32,<1.0 | backend API / ASGI           |
| pydantic          | >=2.9,<3.0                 | схемы и контракты backend    |
| React / react-dom | ^18.3.1                    | фронтенд                     |
| TypeScript        | ^5.6.3                     | typed JS (strict)            |
| Vite              | ^5.4.10                    | сборка и dev (proxy /api)    |
| Vitest            | ^2.1.4                     | тесты frontend               |
| nginx             | 1.27-alpine                | статика + прокси /api (prod) |
| Node              | 22-alpine                  | сборка frontend              |

> Версии фиксируются в `backend/pyproject.toml` и `frontend/package.json`.

## 3. Структура репозитория

```
├── docker-compose.yml   # backend (8000), frontend (3000)
├── .env.example         # значения для compose
├── backend/
│   ├── src/app/         # main.py (health, /api/v1/echo), core/config.py
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
└── frontend/
    ├── src/             # main.tsx, App.tsx, api/client.ts
    ├── Dockerfile + nginx.conf  # сборка → nginx
    ├── vite.config.ts   # proxy /api → localhost:8000
    └── package.json
```

## 4. Ключевые решения (ADR-стиль)

| №   | Дата       | Решение                                        | Обоснование                                |
| --- | ---------- | ---------------------------------------------- | ------------------------------------------ |
| 1   | 2026-10-28 | Monorepo backend+frontend                      | единый контракт, атомарные PR              |
| 2   | 2026-10-28 | Frontend собирается в статику, раздаётся nginx | простой деплой, кэш, единая точка входа    |
| 3   | 2026-10-28 | nginx проксирует `/api` → backend              | frontend не знает адрес backend (нет CORS) |
| 4   | 2026-10-28 | TS strict + Pydantic — два зеркала контракта   | безопасность типов с обеих сторон          |
| 5   | 2026-10-28 | vite dev-proxy повторяет nginx-маршрутизацию   | паритет dev/prod                           |

## 5. Потоки данных

```
Docker: nginx (:3001, FRONTEND_PORT) → /api/** → backend:8000 (внутри сети)
                                   → /       → статические файлы React
API напрямую: BACKEND_PORT (:8001 по умолчанию)
Dev: Vite (:5173) → proxy /api → backend (:8000 локально)
```

**Запрещено:** прямые вызовы backend с фронтенда вне `/api`-префикса.

## 6. Конфигурация и окружение

| Переменная                | Где                | Назначение     | Пример               |
| ------------------------- | ------------------ | -------------- | -------------------- |
| `APP_NAME`, `APP_VERSION` | backend env        | имя/версия API | `template-fullstack` |
| `VITE_API_BASE_URL`       | frontend build arg | base API URL   | `/api`               |
| `HOST`/`PORT`             | backend env        | bind           | `0.0.0.0`/`8000`     |

## 7. Сборка и запуск

```bash
# полный стек
docker compose up --build          # frontend :3000, API :8000

# раздельная разработка
cd backend && uv sync && uv run make dev
cd frontend && npm ci && npm run dev
```

## 8. Границы расширения

- **Без согласования:** новые эндпоинты/компоненты в рамках подсистем,
  новые тесты, UI-страницы ходят в существующий API.
- **Через карточку:** добавление БД/очередей, аутентификация, смена способа
  раздачи frontend, изменение docker-compose-сервисов, ломающие изменения
  контракта.

## 9. Известные ограничения

- Маршруты `/api/health` и `/api/v1/echo` — учебные; заменяются предметными.
- Нет аутентификации и БД по умолчанию (добавляются карточками).
- `package-lock.json`/`uv.lock` генерируются при первом `npm ci`/`uv sync`.
