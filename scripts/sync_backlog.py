#!/usr/bin/env python3
"""Синхронизация BACKLOG.md ↔ SourceCraft Issues (двусторонняя).

BACKLOG.md — единственный источник истины. Скрипт даёт три режима:

  python scripts/sync_backlog.py --org <org> --repo <repo> diff
      Показать расхождения между локальным BACKLOG.md и Issues.

  python scripts/sync_backlog.py --org <org> --repo <repo> push [--apply]
      Отправить локальные изменения в SourceCraft. Без --apply — dry-run.

  python scripts/sync_backlog.py --org <org> --repo <repo> pull
      Обновить BACKLOG.md статусами/ID из SourceCraft.

Настройки (env):
  SOURCECRAFT_BASE_URL   базовый URL API (по умолчанию https://api.sourcecraft.ru)
  SOURCECRAFT_TOKEN      токен доступа (обязателен)

ВАЖНО: пути эндпоинтов зависят от версии API SourceCraft (v2) и должны быть
сверены с документацией. Класс SourceCraftClient — единственное место, где
описывается транспорт.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin

# --- Маппинги статусов и приоритетов -----------------------------------------

# local -> SourceCraft (системные статусы SourceCraft: open, inProgress, paused,
# closed, declined, duplicate)
STATUS_TO_SC: dict[str, str] = {
    "backlog": "open",
    "in_progress": "inProgress",
    "review": "open",
    "done": "closed",
    "cancelled": "declined",
}
SC_TO_STATUS: dict[str, str] = {
    "open": "backlog",
    "inprogress": "in_progress",
    "paused": "in_progress",
    "closed": "done",
    "declined": "cancelled",
    "duplicate": "cancelled",
}

# local -> SourceCraft (приоритеты SourceCraft: trivial, minor, normal,
# critical, blocker)
PRIORITY_TO_SC: dict[str, str] = {
    "low": "trivial",
    "normal": "normal",
    "high": "critical",
    "critical": "blocker",
}
SC_TO_PRIORITY: dict[str, str] = {v: k for k, v in PRIORITY_TO_SC.items()}

VALID_STATUSES = {"backlog", "in_progress", "review", "done", "cancelled"}
VALID_PRIORITIES = {"low", "normal", "high", "critical"}


# --- Модель -------------------------------------------------------------------


@dataclass
class BacklogItem:
    """Карточка бэклога из BACKLOG.md."""

    id: str
    title: str
    status: str = "backlog"
    priority: str = "normal"
    backlog_id: str = ""
    labels: list[str] = field(default_factory=list)
    description: str = ""


_HEADER_RE = re.compile(r"^### \[([A-Z]+-\d+)\]\s+(.+)$")
_FIELD_RE = re.compile(r"^-\s+\*\*([^*]+):\*\*\s*(.*)$")


def parse_backlog(text: str) -> list[BacklogItem]:
    """Разбирает BACKLOG.md в структурированные карточки."""
    items: list[BacklogItem] = []
    current: BacklogItem | None = None
    description_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        m = _HEADER_RE.match(line)
        if m:
            if current is not None:
                current.description = "\n".join(description_lines).strip()
                items.append(current)
            current = BacklogItem(id=m.group(1), title=m.group(2).strip())
            description_lines = []
            continue
        if current is None:
            continue
        f = _FIELD_RE.match(line)
        if f:
            key, value = f.group(1).strip(), f.group(2).strip()
            if key == "Статус":
                current.status = _normalize(value, VALID_STATUSES, "backlog")
            elif key == "Приоритет":
                current.priority = _normalize(value, VALID_PRIORITIES, "normal")
            elif key == "backlog-id":
                current.backlog_id = value
            elif key == "Метки":
                current.labels = [x.strip() for x in value.split(",") if x.strip()]
        else:
            description_lines.append(line)

    if current is not None:
        current.description = "\n".join(description_lines).strip()
        items.append(current)
    return items


def _normalize(value: str, allowed: set[str], default: str) -> str:
    v = value.strip("`").strip().lower()
    return v if v in allowed else default


def format_backlog(path: Path, items: list[BacklogItem]) -> str:
    """Формирует текст BACKLOG.md (заголовок — из существующего файла)."""
    original = path.read_text(encoding="utf-8")
    header_end = original.find("\n## Карточки")
    header = (
        original[: header_end + len("\n## Карточки")] if header_end != -1 else "# Бэклог\n\n## Карточки"
    )

    blocks: list[str] = [header]
    for item in items:
        lines = [f"### [{item.id}] {item.title}", ""]
        lines.append(f"- **Статус:** `{item.status}`")
        lines.append(f"- **Приоритет:** `{item.priority}`")
        if item.backlog_id:
            lines.append(f"- **backlog-id:** `{item.backlog_id}`")
        if item.labels:
            lines.append(f"- **Метки:** {', '.join(item.labels)}")
        if item.description:
            body = ["**Описание:**", "", item.description]
            lines.extend(body)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


# --- Расхождения --------------------------------------------------------------


@dataclass
class Change:
    kind: Literal["create", "update", "close", "reopen", "noop"]
    item: BacklogItem
    fields: list[str] = field(default_factory=list)


def build_changes(local: list[BacklogItem], remote: dict[str, BacklogItem]) -> list[Change]:
    """Вычисляет расхождения local (BACKLOG.md) относительно remote (Issues)."""
    changes: list[Change] = []
    for item in local:
        remote_item = remote.get(item.id)
        if remote_item is None:
            changes.append(Change(kind="create", item=item))
            continue
        fields: list[str] = []
        if item.title != remote_item.title:
            fields.append("title")
        if item.priority != remote_item.priority:
            fields.append("priority")
        if item.status != remote_item.status:
            fields.append("status")
        if item.labels != remote_item.labels:
            fields.append("labels")
        kind: Literal["update", "noop"] = "update" if fields else "noop"
        changes.append(Change(kind=kind, item=item, fields=fields))
    return changes


def print_changes(changes: list[Change]) -> None:
    if not changes:
        print("Расхождений нет.")
        return
    for c in changes:
        if c.kind == "create":
            print(f"[create] {c.item.id} {c.item.title}")
        elif c.kind == "noop":
            continue
        else:
            print(f"[update] {c.item.id} {c.item.title} -> {', '.join(c.fields)}")


# --- Транспорт (SourceCraft API v2) -------------------------------------------

# Эндпоинты зависят от версии API — сверьте с документацией SourceCraft.
ISSUES_LIST_URL = "/api/v2/repos/{org}/{repo}/issues"
ISSUE_URL = "/api/v2/repos/{org}/{repo}/issues/{issue_id}"


class SourceCraftClient:
    """Тонкий HTTP-клиент SourceCraft API (только stdlib)."""

    def __init__(
        self,
        org: str,
        repo: str,
        base_url: str | None = None,
        token: str | None = None,
    ) -> None:
        self.org = org
        self.repo = repo
        self.base_url = (base_url or os.environ.get("SOURCECRAFT_BASE_URL") or
                         "https://api.sourcecraft.ru").rstrip("/")
        self.token = token or os.environ.get("SOURCECRAFT_TOKEN") or ""
        if not self.token:
            raise ValueError("Укажите SOURCECRAFT_TOKEN (env) или --token")

    def _request(self, method: str, url: str, payload: dict | None = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:  # noqa: S310
                body = resp.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"SourceCraft API {exc.code}: {detail}") from exc

    def list_issues(self) -> dict[str, BacklogItem]:
        url = urljoin(self.base_url, ISSUES_LIST_URL.format(org=self.org, repo=self.repo))
        data = self._request("GET", url)
        results = data.get("issues", data.get("items", []))
        remote: dict[str, BacklogItem] = {}
        for raw in results:
            item = _remote_to_local(raw)
            if item is not None:
                remote[item.id] = item
        return remote

    def create_issue(self, item: BacklogItem) -> None:
        url = urljoin(self.base_url, ISSUES_LIST_URL.format(org=self.org, repo=self.repo))
        payload = {
            "title": f"[{item.id}] {item.title}",
            "status": STATUS_TO_SC[item.status],
            "priority": PRIORITY_TO_SC[item.priority],
            "description": item.description or "",
        }
        self._request("POST", url, payload)

    def update_issue(self, item: BacklogItem, issue_id: str, fields: list[str]) -> None:
        url = urljoin(
            self.base_url, ISSUE_URL.format(org=self.org, repo=self.repo, issue_id=issue_id)
        )
        payload: dict = {}
        if "title" in fields:
            payload["title"] = f"[{item.id}] {item.title}"
        if "priority" in fields:
            payload["priority"] = PRIORITY_TO_SC[item.priority]
        if "status" in fields:
            payload["status"] = STATUS_TO_SC[item.status]
        if payload:
            self._request("PATCH", url, payload)


def _remote_to_local(raw: dict) -> BacklogItem | None:
    """Преобразует issue SourceCraft в BacklogItem (по ID в заголовке [XXX-NNN])."""
    title = str(raw.get("title", ""))
    m = re.match(r"\[([A-Z]+-\d+)\]\s*(.*)", title)
    if not m:
        return None
    status_raw = str(raw.get("status", "open")).lower()
    priority_raw = str(raw.get("priority", "normal")).lower()
    return BacklogItem(
        id=m.group(1),
        title=m.group(2).strip(),
        status=SC_TO_STATUS.get(status_raw, "backlog"),
        priority=SC_TO_PRIORITY.get(priority_raw, "normal"),
        backlog_id=str(raw.get("id", "")),
    )


# --- CLI ----------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=Path("BACKLOG.md"))
    parser.add_argument("--org", required=True, help="Organization slug")
    parser.add_argument("--repo", required=True, help="Repository slug")
    parser.add_argument("--token", default=None, help="Токен (или env SOURCECRAFT_TOKEN)")
    parser.add_argument("--base-url", default=None, help="API base (или env SOURCECRAFT_BASE_URL)")
    parser.add_argument("mode", choices=["diff", "push", "pull"])
    parser.add_argument("--apply", action="store_true", help="push: применить изменения (иначе dry-run)")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.file.exists():
        print(f"Файл не найден: {args.file}", file=sys.stderr)
        return 2

    local = parse_backlog(args.file.read_text(encoding="utf-8"))
    client = SourceCraftClient(args.org, args.repo, args.base_url, args.token)

    if args.mode == "diff":
        remote = client.list_issues()
        changes = build_changes(local, remote)
        print_changes(changes)
        return 0

    if args.mode == "push":
        remote = client.list_issues()
        changes = build_changes(local, remote)
        creates = [c for c in changes if c.kind == "create"]
        updates = [c for c in changes if c.kind == "update"]
        print(f"Будет создано: {len(creates)}, обновлено: {len(updates)}")
        if not args.apply:
            print("DRY-RUN: добавьте --apply для применения.")
            return 0
        for c in creates:
            client.create_issue(c.item)
        for c in updates:
            client.update_issue(c.item, c.item.backlog_id, c.fields)
        return 0

    # pull: обновить BACKLOG.md статусами и backlog-id из SourceCraft.
    remote = client.list_issues()
    merged: list[BacklogItem] = []
    for item in local:
        remote_item = remote.get(item.id)
        if remote_item is not None:
            item.status = remote_item.status
            item.priority = remote_item.priority
            item.backlog_id = remote_item.backlog_id
        merged.append(item)
    args.file.write_text(format_backlog(args.file, merged), encoding="utf-8")
    print(f"BACKLOG.md обновлён: {len(merged)} карточек.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
