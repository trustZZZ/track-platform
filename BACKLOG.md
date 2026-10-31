# Бэклог (template-fullstack)

> **Источник истины** о задачах проекта. Синхронизация с SourceCraft Issues —
> скриптом `scripts/sync_backlog.py`.

## Статусы и приоритеты

- Статусы: `backlog` → `in_progress` → `review` → `done`; `cancelled` (с причиной).
- Приоритеты: `critical` → `high` → `normal` → `low`.

## Соглашения

1. ID: префикс `FSTACK-` + номер.
2. `backlog-id` (UUID) — техническое поле синхронизации, руками не менять.
3. Новые карточки — в конец. Удалять нельзя → `cancelled` + причина.
4. `done` — по Definition of Done из `docs/constraints.md`.

## Карточки

### [FSTACK-001] Инициализация проекта из шаблона

- **Статус:** `done`
- **Приоритет:** `high`
- **Оценка:** M
- **backlog-id:** _(присвоится при первой синхронизации)_

**Описание:**
Проект скопирован из шаблона template-fullstack (шаблон не изменялся) в
`platform/`: переименование в `track-platform`, проверка backend (pytest/mypy/ruff).

**Объем работ:**

- [x] Переименование backend/frontend пакетов и заголовков
- [x] Backend: venv + pip (uv не используется — см. FSTACK-007); `frontend: npm ci` — при старте работ над UI (E2/E4)
- [x] Обновление `README.md`, `TECHNICAL.md`, `BACKLOG.md`

**Acceptance Criteria:**

- [x] Backend проверки зелёные (15 passed; frontend — на этапе UI)
- [x] Имена не содержат `template` (кроме исторических упоминаний источника)
- [ ] Бэклог актуализирован

### [FSTACK-002] Предметная сущность сквозь стек

- **Статус:** `backlog`
- **Приоритет:** `high`
- **Оценка:** L

**Описание:**
Первая предметная сущность: Pydantic-схема + маршруты backend, TS-типы +
`client.ts` + UI на frontend, тесты с обеих сторон.

**Acceptance Criteria:**

- [ ] CRUD доступен через UI
- [ ] Тесты backend (>=70%) и frontend (Vitest)
- [ ] `TECHNICAL.md` обновлён

### [FSTACK-003] База данных и миграции

- **Статус:** `backlog`
- **Приоритет:** `high`
- **Оценка:** L

**Описание:**
Подключение Postgres (docker-compose сервис), SQLAlchemy async, Alembic,
хранение предметных данных.

**Acceptance Criteria:**

- [ ] Сервис `db` в compose
- [ ] Миграции применяются при старте
- [ ] Тесты на репозиторий

### [FSTACK-004] Авторизация (JWT)

- **Статус:** `backlog`
- **Приоритет:** `high`
- **Оценка:** L

**Описание:**
Регистрация/вход, JWT для backend, защита маршрутов, хранение токена и
401-обработка на frontend.

**Acceptance Criteria:**

- [ ] Защищённые маршруты требуют токен
- [ ] UI: форма входа, редирект при 401

### [FSTACK-005] Первый релиз

- **Статус:** `backlog`
- **Приоритет:** `normal`
- **Оценка:** S

**Описание:**
Первый тег, релиз, docker-образы backend и frontend, проверка CI.

**Acceptance Criteria:**

- [ ] Тег выпущен, CI зелёный
- [ ] `docker compose up` работает из релиза

### [FSTACK-006] Документация по итогам первого спринта

- **Статус:** `backlog`
- **Приоритет:** `low`
- **Оценка:** S

**Описание:**
Ревизия TECHNICAL.md, constraints.md, README.md по фактическому состоянию.

**Acceptance Criteria:**

- [ ] Документы отражают реальную архитектуру

### [FSTACK-007] Docker-сборка без uv.lock, порты без конфликтов

- **Статус:** `done`
- **Приоритет:** `high`
- **Оценка:** S

**Описание:**
Первая сборка `docker compose up --build` падала: Dockerfile копировал
`uv.lock`, который не генерируется (проект ведётся на pip, без uv). Также
порты 3000/8000 конфликтовали с другим проектом на машине.

**Объем работ:**

- [x] `backend/Dockerfile`: сборка без `uv.lock` (`uv sync` разрешает зависимости при сборке)
- [x] `docker-compose.yml`: порты вынесены в `BACKEND_PORT` (8001) / `FRONTEND_PORT` (3001)
- [x] Контент-бандл и БД кладутся внутрь backend-контейнера (content.json в пакете app, SQLite /app)
- [x] README/TECHNICAL обновлены под новые порты

**Acceptance Criteria:**

- [x] `docker compose up -d --build` собирается и поднимается
- [x] Фикс сборки фронта в чистом окружении: `@types/node` + `"types": ["node"]`
      в tsconfig (process в vite.config)
- [ ] Ручная проверка: frontend :3001 отвечает, API :8001/api/health = ok
      (проверка за пользователем — порты его машины)

**Известная инфраструктурная проблема (не проекта):** при экспорте образа
`failed to prepare extraction snapshot ... parent snapshot does not exist` —
повреждён кэш BuildKit в Docker Desktop (типично при параллельных сборках
нескольких проектов). Лечение: перезапуск Docker Desktop → `docker compose
build --no-cache frontend` → при повторении `docker builder prune -f`
(внимание: сбросит кэш сборок и второго проекта).

### [FSTACK-008] MVP платформы: этапы E2–E7 (план MVP)

- **Статус:** `in_progress`
- **Приоритет:** `high`
- **Оценка:** XL

**Описание:**
Реализация MVP платформы трека (см. README, таблицу этапов): E1 контент-пайплайн
и E3 OAuth/прогресс — сделаны (в рамках карточек 001/007 infrastructure);
остались: E2 UI каталога/урока, E4 автопроверка (self-check готов в API,
Pyodide для L1), E5 роутер, E6 бейджи, E7 деплой VPS (PostgreSQL + HTTPS).

**Acceptance Criteria:**

- [ ] Ученик проходит урок в UI и отмечает прогресс
- [ ] L1-задача проверяется в браузере (Pyodide)
- [ ] Роутер рекомендует пролёт; бейджи отображаются
- [ ] Деплой на VPS с HTTPS
