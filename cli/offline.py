"""Durable local task cache and an ordered outbox, isolated by API and account."""

import base64
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from platformdirs import user_data_path

from cli import api_client, config, settings


def _credentials() -> tuple[str, str]:
    credentials = config.load_credentials()
    token = credentials.get("access_token")
    if not token:
        raise ValueError("Not authenticated. Run `flunky login` first.")
    try:
        part = token.split(".")[1]
        subject = str(json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))["sub"])
    except (ValueError, KeyError, IndexError):
        subject = hashlib.sha256(token.encode()).hexdigest()
    key = hashlib.sha256((settings.api_url() + ":" + subject).encode()).hexdigest()[:24]
    return token, key


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    _, key = _credentials()
    directory = Path(os.environ.get("FLUNKY_DATA_DIR", str(user_data_path("flunky"))))
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"tasks-{key}.sqlite3"
    connection = sqlite3.connect(path, timeout=10)
    os.chmod(path, 0o600)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, method TEXT NOT NULL, task_id INTEGER, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS id_map (local_id INTEGER PRIMARY KEY, remote_id INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL, payload TEXT NOT NULL, action TEXT NOT NULL);
        """)
        with connection:
            yield connection
    finally:
        connection.close()


def _put(db: sqlite3.Connection, task: dict[str, Any]) -> None:
    db.execute("INSERT OR REPLACE INTO tasks VALUES (?,?)", (task["id"], json.dumps(task)))


def _remote(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    token, _ = _credentials()
    try:
        token = config.load_token() or token
    except api_client.APIError as exc:
        if exc.status_code is not None:
            raise
    return api_client._request(
        method, "/v1/tasks" + path, token=token, payload=payload, params=params
    )


def _offline(exc: api_client.APIError) -> bool:
    return exc.status_code is None and str(exc).startswith("Can't reach")


def list_tasks(**filters: Any) -> tuple[list[dict[str, Any]], bool]:
    with database() as db:
        pending = db.execute("SELECT count(*) FROM outbox").fetchone()[0]
        if not pending:
            try:
                rows = _remote("GET", "", params=filters)
                for row in rows:
                    _put(db, row)
                return list(rows), False
            except api_client.APIError as exc:
                if not _offline(exc):
                    raise
        rows = [json.loads(row["data"]) for row in db.execute("SELECT data FROM tasks")]
        rows = [
            row
            for row in rows
            if bool(row.get("deleted_at")) == bool(filters.get("deleted", False))
        ]
        for key in ("priority",):
            if filters.get(key) is not None:
                rows = [row for row in rows if row.get(key) == filters[key]]
        if filters.get("completed") is not None:
            rows = [row for row in rows if row.get("is_completed", False) == filters["completed"]]
        if filters.get("tag"):
            rows = [row for row in rows if filters["tag"] in row.get("tags", [])]
        if filters.get("search"):
            rows = [row for row in rows if filters["search"].lower() in row["title"].lower()]
        for key, before in [("due_before", True), ("due_after", False)]:
            if filters.get(key):
                rows = [
                    row
                    for row in rows
                    if row.get("due_date")
                    and (
                        row["due_date"] <= filters[key]
                        if before
                        else row["due_date"] >= filters[key]
                    )
                ]
        sort = filters.get("sort", "created_at")
        key = sort.lstrip("-")
        rows.sort(
            key=lambda row: (
                {"high": 0, "medium": 1, "low": 2}.get(row.get("priority"), 1)
                if key == "priority"
                else str(row.get(key) or "9999"),
                row["id"],
            ),
            reverse=sort.startswith("-"),
        )
        offset, limit = filters.get("offset", 0), filters.get("limit", 50)
        return rows[offset : offset + limit], True


def get_task(task_id: int) -> tuple[dict[str, Any], bool]:
    with database() as db:
        if not db.execute("SELECT 1 FROM outbox LIMIT 1").fetchone() and task_id > 0:
            try:
                task = _remote("GET", f"/{task_id}")
                _put(db, task)
                return dict(task), False
            except api_client.APIError as exc:
                if not _offline(exc):
                    raise
        row = db.execute("SELECT data FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(
                f"Task {task_id} is not cached. Connect to the server and run `flunky list`."
            )
        return json.loads(row["data"]), True


def add_task(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    payload = {**payload, "client_id": str(uuid4())}
    with database() as db:
        if not db.execute("SELECT 1 FROM outbox LIMIT 1").fetchone():
            try:
                task = _remote("POST", "", payload)
                _put(db, task)
                return dict(task), False
            except api_client.APIError as exc:
                if not _offline(exc):
                    raise
        task_id = min(0, db.execute("SELECT coalesce(min(id),0) FROM tasks").fetchone()[0]) - 1
        task = {
            **payload,
            "id": task_id,
            "title": payload["task_title"],
            "description": payload.get("task_description"),
            "is_completed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _put(db, task)
        db.execute(
            "INSERT INTO outbox(method,task_id,payload) VALUES (?,?,?)",
            ("POST", task_id, json.dumps(payload)),
        )
        return task, True


def mutate(
    task_id: int, payload: dict[str, Any], action: str = "update", *, record: bool = True
) -> tuple[dict[str, Any], bool]:
    previous, cached = get_task(task_id)
    method = "DELETE" if action == "delete" else ("POST" if action == "restore" else "PUT")
    suffix = f"/{task_id}" + ("/restore" if action == "restore" else "")
    offline = cached
    task = {**previous, **payload}
    if action == "delete":
        task["deleted_at"] = datetime.now(timezone.utc).isoformat()
    elif action == "restore":
        task["deleted_at"] = None
    if not cached:
        try:
            result = _remote(method, suffix, payload or None)
            if result:
                task = result
        except api_client.APIError as exc:
            if not _offline(exc):
                raise
            offline = True
    with database() as db:
        if offline:
            db.execute(
                "INSERT INTO outbox(method,task_id,payload) VALUES (?,?,?)",
                (
                    method + ("_restore" if action == "restore" else ""),
                    task_id,
                    json.dumps(payload),
                ),
            )
        _put(db, task)
        if record:
            db.execute(
                "INSERT INTO history(task_id,payload,action) VALUES (?,?,?)",
                (task_id, json.dumps(previous), action),
            )
    return task, offline


def undo() -> tuple[dict[str, Any], bool]:
    with database() as db:
        row = db.execute("SELECT * FROM history ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            raise ValueError("Nothing to undo in this account.")
        previous = json.loads(row["payload"])
        mapping = db.execute(
            "SELECT remote_id FROM id_map WHERE local_id=?", (row["task_id"],)
        ).fetchone()
        task_id = mapping[0] if mapping else row["task_id"]
    if row["action"] == "delete":
        # Cached soft-deleted tasks remain available to restoration.
        with database() as db:
            cached = db.execute("SELECT data FROM tasks WHERE id=?", (task_id,)).fetchone()
            pending = db.execute("SELECT 1 FROM outbox LIMIT 1").fetchone() is not None
        if cached is None:
            raise ValueError("Deleted task is not cached; use the server restore endpoint.")
        try:
            result = _remote("POST", f"/{task_id}/restore") if task_id > 0 and not pending else None
        except api_client.APIError as exc:
            if not _offline(exc):
                raise
            result = None
        with database() as db:
            task = result or {**json.loads(cached[0]), "deleted_at": None}
            _put(db, task)
            if result is None:
                db.execute(
                    "INSERT INTO outbox(method,task_id,payload) VALUES (?,?,?)",
                    ("POST_restore", task_id, "{}"),
                )
        result_pair = (task, result is None)
    else:
        fields = {
            key: previous.get(key)
            for key in (
                "title",
                "description",
                "is_completed",
                "priority",
                "due_date",
                "tags",
                "notes",
            )
            if key in previous
        }
        result_pair = mutate(task_id, fields, record=False)
    with database() as db:
        db.execute("DELETE FROM history WHERE id=?", (row["id"],))
    return result_pair


def sync() -> dict[str, int]:
    count = 0
    with database() as db:
        queue = list(db.execute("SELECT * FROM outbox ORDER BY id"))
    for item in queue:
        with database() as db:
            mapped = db.execute(
                "SELECT remote_id FROM id_map WHERE local_id=?", (item["task_id"],)
            ).fetchone()
        task_id = mapped[0] if mapped else item["task_id"]
        method = item["method"]
        path = (
            ""
            if method == "POST"
            else f"/{task_id}" + ("/restore" if method == "POST_restore" else "")
        )
        try:
            result = _remote(method.split("_")[0], path, json.loads(item["payload"]))
        except api_client.APIError as exc:
            if method != "DELETE" or exc.status_code != 404:
                raise
            result = None
        with database() as db:
            if method == "POST":
                db.execute(
                    "INSERT OR REPLACE INTO id_map VALUES (?,?)", (item["task_id"], result["id"])
                )
                db.execute("DELETE FROM tasks WHERE id=?", (item["task_id"],))
            if result:
                _put(db, result)
            db.execute("DELETE FROM outbox WHERE id=?", (item["id"],))
        count += 1
    return {"synced": count, "pending": 0}
