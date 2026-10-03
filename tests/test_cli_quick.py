import json
from datetime import date
from unittest.mock import Mock

import httpx
import pytest
from typer.testing import CliRunner

from cli import api_client, config, main, offline, settings, ui

BASE = api_client.BASE_URL
TASK = {
    "id": 1,
    "title": "Release",
    "priority": "high",
    "tags": ["backend"],
    "due_date": date.today().isoformat(),
    "is_completed": False,
    "created_at": "2026-10-03T00:00:00Z",
}
runner = CliRunner()


@pytest.fixture(autouse=True)
def quick_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    config.save_token("test-token")


def invoke(*args):
    result = runner.invoke(main.app, list(args))
    assert result.exit_code == 0, result.output
    return result


def test_global_json_anywhere_and_quiet(respx_mock):
    respx_mock.get(BASE + "/v1/tasks").respond(200, json=[TASK])
    for args in [("list", "--json"), ("--json", "list"), ("list", "--no-color", "--json")]:
        data = json.loads(invoke(*args).stdout)
        assert data["tasks"][0]["title"] == "Release"
        assert data["offline"] is False
    assert invoke("list", "--quiet").stdout == ""
    result = runner.invoke(main.app, ["add", "", "--json"])
    assert result.exit_code == 1
    assert "error" in json.loads(result.stdout)
    assert "Traceback" not in result.output


def test_quick_task_surface(respx_mock, monkeypatch):
    post = respx_mock.post(BASE + "/v1/tasks").respond(201, json=TASK)
    get = respx_mock.get(BASE + "/v1/tasks/1").respond(200, json=TASK)
    listing = respx_mock.get(BASE + "/v1/tasks").respond(200, json=[TASK])
    put = respx_mock.put(BASE + "/v1/tasks/1").respond(200, json={**TASK, "is_completed": True})
    delete = respx_mock.delete(BASE + "/v1/tasks/1").respond(204)
    restore = respx_mock.post(BASE + "/v1/tasks/1/restore").respond(200, json=TASK)
    assert (
        json.loads(
            invoke(
                "add", "Release", "-p", "high", "-d", "tomorrow", "-t", "backend", "--json"
            ).stdout
        )["id"]
        == 1
    )
    assert "client_id" in json.loads(post.calls.last.request.content)
    invoke("today")
    invoke("upcoming")
    invoke("show", "1")
    invoke("done", "1")
    assert json.loads(put.calls.last.request.content)["is_completed"]
    invoke("undo")
    invoke("edit", "1", "--title", "New", "--notes", "Context", "-t", "backend")
    invoke("rm", "1", "--yes")
    invoke("undo")
    assert delete.called and restore.called and get.called and listing.called
    monkeypatch.setattr(
        "cli.commands.questionary.autocomplete", lambda *a, **k: Mock(ask=lambda: "1 · Release")
    )
    invoke("show")
    assert "Synced 0" in invoke("sync").output


@pytest.mark.parametrize(
    "args",
    [
        ["add", "x", "-p", "urgent"],
        ["add", "x", "-d", "not a date"],
        ["list", "--completed", "wat"],
        ["list", "--sort", "bogus"],
        ["edit", "1"],
        ["edit", "1", "-p", "urgent"],
        ["tui"],
        ["config", "get", "missing"],
        ["config", "set", "bad", "v"],
        ["config", "profile", "missing"],
        ["completion", "install", "bad"],
    ],
)
def test_quick_errors(args):
    result = runner.invoke(main.app, [*args, "--json"])
    assert result.exit_code == 1, result.output
    assert "error" in json.loads(result.stdout)


def test_profiles_and_configuration(monkeypatch):
    invoke("config", "set", "api_url", "http://127.0.0.1:9000")
    assert json.loads(invoke("config", "get", "api_url", "--json").stdout)["api_url"].endswith(
        ":9000"
    )
    assert settings.api_url() == "http://127.0.0.1:9000"
    invoke("config", "profile", "staging")
    with pytest.raises(ValueError, match="no API URL"):
        settings.api_url()
    invoke("config", "set", "api_url", "https://staging.example.com")
    assert settings.api_url() == "https://staging.example.com"
    monkeypatch.setenv("FLUNKY_API_URL", "https://env.example.com")
    assert settings.api_url() == "https://env.example.com"
    assert "profiles" in json.loads(invoke("config", "list", "--json").stdout)
    monkeypatch.setenv("FLUNKY_API_URL", "http://remote.example.com")
    with pytest.raises(ValueError, match="HTTPS"):
        settings.api_url()


def test_doctor_and_completion(respx_mock, monkeypatch, tmp_path):
    respx_mock.get(BASE + "/ready").respond(200, json={"status": "ready"})
    respx_mock.get(BASE + "/v1/auth/me").respond(200, json={"username": "alice"})
    assert json.loads(invoke("doctor", "--json").stdout)["auth"] == "alice"
    assert "Installed" in invoke("completion", "install", "zsh").output
    assert (tmp_path / "completions/_flunky").is_file()


def test_offline_outbox_and_negative_id_mapping(respx_mock):
    create = respx_mock.post(BASE + "/v1/tasks").mock(side_effect=httpx.ConnectError("offline"))
    result = json.loads(
        invoke("add", "Offline task", "-d", "tomorrow", "-t", "backend", "--json").stdout
    )
    assert result["id"] == -1 and result["offline"]
    invoke("done", "--", "-1")
    invoke("edit", "--title", "Edited offline", "--", "-1")
    result = json.loads(
        invoke(
            "list", "--completed", "true", "--tag", "backend", "--search", "edited", "--json"
        ).stdout
    )
    assert result["offline"] and result["tasks"][0]["title"] == "Edited offline"
    invoke("undo")
    create.respond(201, json={**TASK, "id": 42, "title": "Offline task"})
    update = respx_mock.put(BASE + "/v1/tasks/42").respond(
        200, json={**TASK, "id": 42, "is_completed": True}
    )
    result = json.loads(invoke("sync", "--json").stdout)
    assert result["synced"] == 4 and update.call_count == 3
    assert offline.sync()["pending"] == 0
    with offline.database() as db:
        assert db.execute("SELECT count(*) FROM outbox").fetchone()[0] == 0
        assert db.execute("SELECT remote_id FROM id_map WHERE local_id=-1").fetchone()[0] == 42


def test_offline_delete_undo_queue_order(respx_mock):
    respx_mock.post(BASE + "/v1/tasks").mock(side_effect=httpx.ConnectError("offline"))
    invoke("add", "Temporary")
    invoke("rm", "--yes", "--", "-1")
    invoke("undo")
    rows, cached = offline.list_tasks()
    assert cached and len(rows) == 1 and rows[0]["deleted_at"] is None
    with offline.database() as db:
        assert [r[0] for r in db.execute("SELECT method FROM outbox ORDER BY id")] == [
            "POST",
            "DELETE",
            "POST_restore",
        ]


def test_offline_permission_errors_are_not_queued(respx_mock):
    respx_mock.post(BASE + "/v1/tasks").respond(403)
    result = runner.invoke(main.app, ["add", "Forbidden", "--json"])
    assert result.exit_code == 1
    with offline.database() as db:
        assert db.execute("SELECT count(*) FROM outbox").fetchone()[0] == 0


def test_server_creation_idempotency(client):
    from test_task import create_user_and_get_token

    headers = create_user_and_get_token(client)
    payload = {"task_title": "Retry safely", "client_id": "12345678-1234-1234-1234-123456789012"}
    first = client.post("/v1/tasks", json=payload, headers=headers)
    second = client.post("/v1/tasks", json=payload, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get("/v1/tasks", headers=headers).json()) == 1


async def test_tui_keyboard_and_search(monkeypatch):
    from textual.widgets import DataTable

    from cli.tui import TaskBoard

    monkeypatch.setattr(offline, "list_tasks", lambda **kw: ([TASK], False))
    monkeypatch.setattr(offline, "get_task", lambda task_id: (TASK, False))
    complete = Mock(return_value=(TASK, False))
    monkeypatch.setattr(offline, "mutate", complete)
    monkeypatch.setattr(offline, "undo", lambda: (TASK, False))
    async with TaskBoard().run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        table = pilot.app.query_one(DataTable)
        assert table.row_count == 1
        table.focus()
        await pilot.press("d")
        assert complete.called
        await pilot.press("u", "/", "r", "e", "l")
        await pilot.pause()


def test_dates_and_ascii(monkeypatch):
    assert ui.relative_date(date.today().isoformat()) == "today"
    assert "in " in ui.relative_date("2099-01-01")
    assert "overdue" in ui.relative_date("2000-01-01")
    monkeypatch.setenv("TERM", "dumb")
    assert ui.relative_date(None) == "-"


def test_fast_launcher(monkeypatch, capsys):
    from cli.entry import main as entry

    monkeypatch.setattr("sys.argv", ["flunky", "--help"])
    entry()
    assert "flunky" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["flunky", "--version"])
    entry()
    assert "0.1.0" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["flunky", "doctor"])
    called = Mock()
    monkeypatch.setattr(main, "app", called)
    entry()
    assert called.called


def test_noninteractive_prompts_and_yes(monkeypatch):
    from cli.ui.prompts import questionary

    ui.configure(set())
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(ValueError, match="Interactive input"):
        questionary.text("title").ask()
    with pytest.raises(ValueError):
        questionary.password("password").ask()
    ui.configure({"--yes"})
    assert questionary.confirm("confirm").ask() is True
    ui.configure(set())


def test_notifier_cache_and_fetch(monkeypatch, tmp_path, respx_mock):
    from cli import updatecheck

    monkeypatch.setenv("FLUNKY_CACHE_DIR", str(tmp_path))
    respx_mock.get("https://pypi.org/pypi/flunky/json").respond(
        200, json={"info": {"version": "0.2.0"}}
    )
    updatecheck.fetch()
    assert json.loads(updatecheck.cache_file().read_text())["version"] == "0.2.0"
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.delenv("CI", raising=False)
    ui.configure(set())
    updatecheck.notify()
    respx_mock.get("https://pypi.org/pypi/flunky/json").respond(500)
    updatecheck.fetch()


def test_completion_explicit_path(tmp_path):
    path = tmp_path / "completion.zsh"
    invoke("completion", "install", "zsh", "--path", str(path))
    assert "flunky" in path.read_text()
    assert (
        runner.invoke(
            main.app, ["completion", "install", "zsh", "--path", str(path), "--json"]
        ).exit_code
        == 1
    )


async def test_tui_search_escape_returns_to_list(monkeypatch):
    from textual.widgets import DataTable, Input

    from cli.tui import TaskBoard

    monkeypatch.setattr(offline, "list_tasks", lambda **kwargs: ([], False))
    board = TaskBoard()
    async with board.run_test() as pilot:
        assert isinstance(board.focused, DataTable)
        await pilot.press("/")
        assert isinstance(board.focused, Input)
        await pilot.press("escape")
        assert isinstance(board.focused, DataTable)
        await pilot.press("q")
