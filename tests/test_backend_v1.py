import os
import sqlite3
import subprocess
import sys
from contextlib import closing

import pytest
from pydantic import ValidationError
from test_task import create_user_and_get_token

from backend.core.config import Settings


def test_rich_tasks_filters_pagination_restore(client):
    headers = create_user_and_get_token(client)
    first = client.post(
        "/v1/tasks",
        headers=headers,
        json={
            "task_title": "A release",
            "priority": "high",
            "tags": ["backend"],
            "due_date": "2026-10-04",
            "notes": "careful",
        },
    ).json()
    second = client.post(
        "/v1/tasks",
        headers=headers,
        json={"task_title": "B docs", "priority": "low", "due_date": "2026-10-08"},
    ).json()
    for query in [
        "priority=high",
        "tag=backend",
        "search=release",
        "due_before=2026-10-05",
        "due_after=2026-10-03&due_before=2026-10-04",
    ]:
        response = client.get("/v1/tasks?" + query, headers=headers)
        assert response.status_code == 200, response.text
        assert [t["id"] for t in response.json()] == [first["id"]]
    response = client.get("/v1/tasks?limit=1&offset=1&sort=title", headers=headers)
    assert response.headers["X-Total-Count"] == "2"
    assert response.json()[0]["id"] == second["id"]
    for sort in ["-title", "priority", "-priority", "updated_at", "-created_at", "due_date"]:
        assert client.get("/v1/tasks?sort=" + sort, headers=headers).status_code == 200
    response = client.put(
        f"/v1/tasks/{first['id']}",
        headers=headers,
        json={"due_date": None, "notes": None, "title": None},
    )
    assert response.json()["due_date"] is None
    assert client.delete(f"/v1/tasks/{first['id']}", headers=headers).status_code == 204
    assert len(client.get("/v1/tasks?deleted=true", headers=headers).json()) == 1
    assert (
        client.post(f"/v1/tasks/{first['id']}/restore", headers=headers).json()["deleted_at"]
        is None
    )
    assert client.get("/v1/tasks?completed=false", headers=headers).headers["X-Total-Count"] == "2"


def test_bulk_atomicity_and_validation(client):
    headers = create_user_and_get_token(client)
    ids = [
        client.post("/v1/tasks", headers=headers, json={"task_title": title}).json()["id"]
        for title in ["one", "two"]
    ]
    assert (
        client.post(
            "/v1/tasks/bulk/complete", headers=headers, json={"ids": [ids[0], 999]}
        ).status_code
        == 404
    )
    assert client.get(f"/v1/tasks/{ids[0]}", headers=headers).json()["is_completed"] is False
    assert (
        client.post("/v1/tasks/bulk/complete", headers=headers, json={"ids": ids}).json()["count"]
        == 2
    )
    assert (
        client.post("/v1/tasks/bulk/delete", headers=headers, json={"ids": ids}).json()["count"]
        == 2
    )
    assert client.get("/v1/tasks", headers=headers).json() == []
    for payload in [
        {"task_title": " "},
        {"task_title": ""},
        {"task_title": "okay", "priority": "urgent"},
    ]:
        response = client.post("/v1/tasks", headers=headers, json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
    assert (
        client.put(f"/v1/tasks/{ids[0]}", headers=headers, json={"title": " "}).status_code == 422
    )
    assert client.get("/v1/tasks?limit=0", headers=headers).status_code == 422


def test_health_readiness_errors(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").status_code == 503
    response = client.get("/not-found")
    assert response.status_code == 404
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert client.get("/v1/tasks").status_code == 401


def test_production_configuration():
    for secret in ["", "dev-secret-change-me", "short"]:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, environment="production", secret_key=secret)
    assert (
        Settings(_env_file=None, environment="production", secret_key="x" * 32).environment
        == "production"
    )
    assert (
        Settings(_env_file=None, database_url="postgresql://localhost/test").database_url
        == "postgresql+asyncpg://localhost/test"
    )
    assert (
        Settings(_env_file=None, database_url="sqlite:///test.db").database_url
        == "sqlite+aiosqlite:///test.db"
    )


def test_migrations_upgrade_downgrade_and_legacy_data(tmp_path):
    db = tmp_path / "migration.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db}"}

    def migrate(*args):
        subprocess.run(
            [sys.executable, "-m", "alembic", *args], env=env, check=True, capture_output=True
        )

    migrate("upgrade", "0001")
    with closing(sqlite3.connect(db)) as connection:
        connection.execute(
            "INSERT INTO users VALUES (1, 'legacy', 'legacy@example.com', 'hash', '2026-01-01')"
        )
        connection.execute("INSERT INTO tasks VALUES (1, 'preserved', NULL, 0, '2026-01-01', 1)")
        connection.commit()
    migrate("upgrade", "head")
    with closing(sqlite3.connect(db)) as connection:
        assert connection.execute("SELECT title, priority, tags FROM tasks").fetchone() == (
            "preserved",
            "medium",
            "[]",
        )
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0004"
    migrate("downgrade", "0001")
    migrate("upgrade", "head")
    migrate("downgrade", "base")
    migrate("upgrade", "head")


async def test_ready_rejects_stale_migrations(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    import backend.main as application

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/ready.db")
    factory = async_sessionmaker(engine)
    monkeypatch.setattr(application, "SessionLocal", factory)
    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE alembic_version(version_num TEXT)"))
        await connection.execute(text("INSERT INTO alembic_version VALUES ('0001')"))
    with TestClient(application.app) as client:
        assert client.get("/ready").status_code == 503
        async with engine.begin() as connection:
            await connection.execute(text("UPDATE alembic_version SET version_num='0004'"))
        assert client.get("/ready").status_code == 200
    await engine.dispose()
