# AGENTS.md — Правила для ИИ-агентов (template-fullstack)

> ОБЯЗАТЕЛЬНО прочитать перед началом любой работы в этом репозитории.

## 1. Обязательные действия перед началом работы

1. Прочитать этот файл.
2. Прочитать [`TECHNICAL.md`](TECHNICAL.md) (архитектура backend/frontend).
3. Прочитать [`docs/constraints.md`](docs/constraints.md) (ограничения).
4. Изучить [`BACKLOG.md`](BACKLOG.md) и выбрать карточку `backlog`.
5. Нет подходящей карточки — создать по формату, затем работать.

## 2. Железные правила

- **Нет карточки в бэклоге — нет задачи.**
- **Monorepo из двух подсистем:** `backend/` и `frontend/`.
  - Backend — FastAPI: логика в сервисах, не в маршрутах.
  - Frontend — React + TS strict: контракты API — в `src/api/client.ts` и Pydantic-схемах backend; **типы/поля не дублировать** произвольно.
- **Связь фронтенд ↔ бэкенд — только через `/api`** (vite-proxy в dev, nginx в prod).
- **API-контракты не ломаются без карточки** (и синхронного обновления клиента).
- **Не менять стек** (FastAPI, React, Vite, nginx) без карточки.
- **Перед сдачей все проверки зелёные (обе подсистемы):**
  ```bash
  cd backend && uv run make check
  cd frontend && npm run typecheck && npm test && npm run build
  ```

## 3. Команды

| Подсистема | Действие | Команда |
|---|---|---|
| backend | установка | `cd backend && uv sync` |
| backend | проверки | `cd backend && uv run make check` |
| backend | dev-сервер | `cd backend && uv run make dev` |
| frontend | установка | `cd frontend && npm ci` |
| frontend | типы | `cd frontend && npm run typecheck` |
| frontend | тесты | `cd frontend && npm test` |
| frontend | сборка | `cd frontend && npm run build` |
| оба | полный стек | `docker compose up --build` |

## 4. Критерии готовности (Definition of Done)

- [ ] Открытая карточка бэклога, связанная с работой.
- [ ] Backend: `ruff`, `mypy`, `pytest` зелёные (покрытие >= 70%).
- [ ] Frontend: `tsc -b`, `vitest run`, `npm run build` зелёные.
- [ ] Изменения контракта — синхронно в Pydantic-схеме и TS-типах.
- [ ] `TECHNICAL.md` / `README.md` актуальны.
- [ ] Карточка: `in_progress` → `review`.

## 5. Чего делать нельзя

- Прятать API-вызовы в компонентах (только через `src/api/`).
- Менять nginx-прокси без карточки (критично для dev/prod паритета).
- Сыпать секреты в `VITE_*` (всё с таким префиксом попадает в бандл).
- Игнорировать ошибки типов TS или mypy.
- Умалчивать о невыполненных шагах или неудачных попытках.
