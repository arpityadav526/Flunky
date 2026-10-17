"""Regression coverage for portable deployment and authentication throttling."""

import subprocess
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.engine import make_url

from backend import container
from backend.core.config import Settings
from backend.core.rate_limit import MemoryRateLimiter
from scripts import setup_container


def test_failure_backoff_on_long_running_host(monkeypatch):
    now = 100_000.0
    monkeypatch.setattr("backend.core.rate_limit.time.monotonic", lambda: now)
    limiter = MemoryRateLimiter()
    for _ in range(5):
        limiter.check("account:alice", 30, 900)
        limiter.failure("account:alice")
        now += 1
    with pytest.raises(HTTPException) as error:
        limiter.check("account:alice", 30, 900)
    assert error.value.status_code == 429
    now += 33
    limiter.check("account:alice", 30, 900)
    limiter.failure("account:alice")
    assert limiter.failures["account:alice"][0] == 6
    now += 1000
    limiter.failure("account:alice")
    assert limiter.failures["account:alice"][0] == 1
    limiter.success("account:alice")
    assert "account:alice" not in limiter.failures


def test_database_password_with_url_delimiters():
    password = "p@ss:/?#% word"
    settings = Settings(
        _env_file=None,
        database_url="postgresql://flunky@db:5432/flunky?sslmode=require",
        database_password=password,
    )
    url = make_url(settings.database_url)
    assert url.password == password
    assert url.host == "db"
    assert url.query == {"ssl": "require"}


def test_container_migrates_before_starting(monkeypatch):
    calls = []
    monkeypatch.setattr(container.subprocess, "run", lambda *a, **kw: calls.append("migrate"))
    monkeypatch.setattr(container.os, "execvp", lambda *a: calls.append(a))
    container.main()
    assert calls[0] == "migrate"
    executable, args = calls[1]
    assert executable == "gunicorn"
    assert args[args.index("--workers") + 1] == "1"


def test_failed_migration_does_not_start_server(monkeypatch):
    monkeypatch.setattr(
        container.subprocess,
        "run",
        Mock(side_effect=subprocess.CalledProcessError(1, "alembic")),
    )
    start = Mock()
    monkeypatch.setattr(container.os, "execvp", start)
    with pytest.raises(subprocess.CalledProcessError):
        container.main()
    start.assert_not_called()


def test_setup_preserves_credentials(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    setup_container.main()
    path = tmp_path / ".env.docker"
    original = path.read_text()
    values = dict(line.split("=", 1) for line in original.splitlines())
    assert len(values["SECRET_KEY"]) == 64
    assert len(values["POSTGRES_PASSWORD"]) == 64
    assert values["SECRET_KEY"] != values["POSTGRES_PASSWORD"]
    setup_container.main()
    assert path.read_text() == original


def test_rate_limiter_bounds_recent_unique_identities(monkeypatch):
    monkeypatch.setattr("backend.core.rate_limit.time.monotonic", lambda: 100_000.0)
    limiter = MemoryRateLimiter()
    for index in range(10_001):
        limiter.check(f"account:{index}")
    assert len(limiter.hits) == 10_000
    assert "account:10000" in limiter.hits
    # Updating a tracked identity must not evict another identity.
    limiter.check("account:10000")
    assert len(limiter.hits) == 10_000
