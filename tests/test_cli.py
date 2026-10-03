"""User-visible command contracts, including both reported regressions."""

import json
from unittest.mock import Mock

import httpx
import pytest
from rich.console import Console
from typer.testing import CliRunner

from cli import api_client, config, main
from cli.ui_theme import custom_theme
from cli.utils import filesystem

TASK = {
    "id": 1,
    "title": "Ship Flunky",
    "description": "Test first",
    "is_completed": False,
    "created_at": "2026-10-03T00:00:00Z",
    "user_id": 1,
}
BASE = api_client.BASE_URL
runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(filesystem, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(filesystem, "PROJECTS_FILE", tmp_path / "projects.json")
    monkeypatch.setattr(
        main,
        "console",
        Console(force_terminal=False, color_system=None, width=100, theme=custom_theme),
    )


@pytest.fixture
def prompts(monkeypatch):
    def install(*answers):
        ask = Mock(side_effect=answers)
        for name in ("text", "password", "confirm"):
            monkeypatch.setattr(main.questionary, name, lambda *a, **kw: Mock(ask=ask))
        return ask

    return install


@pytest.mark.parametrize("status", [200, 204])
def test_delete_accepts_empty_success(status, respx_mock):
    respx_mock.delete(f"{BASE}/tasks/1").respond(status)
    assert api_client.delete_task(1, " token ") is None


@pytest.mark.parametrize(
    "status, message",
    [(401, "Not authenticated"), (403, "Not authorized"), (404, "not found"), (500, "HTTP 500")],
)
def test_delete_rejects_error(status, message, respx_mock):
    respx_mock.delete(f"{BASE}/tasks/1").respond(status, text="not JSON")
    with pytest.raises(api_client.APIError, match=message):
        api_client.delete_task(1, "token")


@pytest.mark.parametrize("completed", [True, False, None])
def test_filter_uses_lowercase(completed, respx_mock):
    route = respx_mock.get(f"{BASE}/tasks").respond(200, json=[])
    assert api_client.get_all_task("token", completed) == []
    params = route.calls.last.request.url.params
    assert "Completed" not in params
    assert params.get("completed") == (None if completed is None else str(completed).lower())


@pytest.mark.parametrize(
    "args, method, path, response, expected",
    [
        (
            ["task", "create", "-t", "Ship Flunky", "-d", "Test first"],
            "POST",
            "/tasks",
            TASK,
            "created successfully",
        ),
        (["task", "list"], "GET", "/tasks", [TASK], "Ship Flunky"),
        (["task", "show", "1"], "GET", "/tasks/1", TASK, "Task Details"),
        (["task", "update", "1", "-t", "Ship"], "PUT", "/tasks/1", TASK, "updated successfully"),
        (["task", "complete", "1"], "PUT", "/tasks/1", TASK, "marked as complete"),
    ],
)
@pytest.mark.parametrize("success", [True, False])
def test_task_commands(args, method, path, response, expected, success, respx_mock):
    config.save_token("token")
    respx_mock.route(method=method, url=f"{BASE}{path}").respond(
        200 if success else 403, json=response if success else {"detail": "Forbidden"}
    )
    result = runner.invoke(main.app, args)
    assert result.exit_code == (0 if success else 1), result.output
    assert expected in result.output if success else expected not in result.output


@pytest.mark.parametrize("status", [204, 401, 403, 404])
def test_delete_command_never_prints_false_success(status, respx_mock):
    config.save_token("token")
    respx_mock.get(f"{BASE}/tasks/1").respond(200, json=TASK)
    respx_mock.delete(f"{BASE}/tasks/1").respond(status)
    result = runner.invoke(main.app, ["task", "delete", "1", "--force"])
    assert result.exit_code == (0 if status == 204 else 1)
    assert ("deleted successfully" in result.output) == (status == 204)


@pytest.mark.parametrize("command", ["register", "login"])
@pytest.mark.parametrize("success", [True, False])
def test_auth_commands(command, success, prompts, respx_mock):
    prompts(
        *(
            ["alice", "a@example.com", "testpass123", "testpass123"]
            if command == "register"
            else ["alice", "testpass123"]
        )
    )
    payload = {"username": "alice"} if command == "register" else {"access_token": "token"}
    respx_mock.post(f"{BASE}/{command}").respond(
        200 if success else 400, json=payload if success else {"detail": "invalid credentials"}
    )
    result = runner.invoke(
        main.app, [command, *(["--with-password"] if command == "login" else [])]
    )
    assert result.exit_code == (0 if success else 1), result.output
    assert ("successful" in result.output) == success


@pytest.mark.parametrize(
    "command,answers",
    [
        ("register", [None]),
        ("register", ["alice", None]),
        ("register", ["alice", "a@b.com", None]),
        ("register", ["alice", "a@b.com", "password", None]),
        ("login", [None]),
        ("login", ["alice", None]),
    ],
)
def test_auth_cancel(command, answers, prompts):
    prompts(*answers)
    assert (
        runner.invoke(
            main.app, [command, *(["--with-password"] if command == "login" else [])]
        ).exit_code
        == 0
    )


def test_logout(respx_mock):
    respx_mock.post(f"{BASE}/v1/auth/logout").respond(204)
    assert "not logged in" in runner.invoke(main.app, ["logout"]).output
    config.save_token("token")
    assert "Logged out" in runner.invoke(main.app, ["logout"]).output
    assert config.load_token() is None


@pytest.mark.parametrize(
    "args",
    [["create"], ["list"], ["show", "1"], ["update", "1"], ["complete", "1"], ["delete", "1"]],
)
def test_unauthenticated_tasks(args):
    assert "login first" in runner.invoke(main.app, ["task", *args]).output


def test_projects(tmp_path):
    assert "No saved projects" in runner.invoke(main.app, ["projects", "list"]).output
    assert runner.invoke(main.app, ["projects", "add", "demo", str(tmp_path)]).exit_code == 0
    result = runner.invoke(main.app, ["projects", "list"])
    assert "demo" in result.output
    assert runner.invoke(main.app, ["projects", "remove", "demo"]).exit_code == 0
    assert runner.invoke(main.app, ["projects", "remove", "missing"]).exit_code == 1
    assert (
        runner.invoke(main.app, ["projects", "add", "demo", str(tmp_path / "missing")]).exit_code
        == 1
    )


def test_dashboard_and_help(snapshot):
    assert runner.invoke(main.app, []).output == snapshot
    assert "0.1.0" in runner.invoke(main.app, ["--version"]).output
    for command in [[], ["task"], ["projects"], ["init"]]:
        assert runner.invoke(main.app, [*command, "--help"]).exit_code == 0


@pytest.mark.parametrize(
    "command,response", [(["task", "list"], [TASK]), (["task", "show", "1"], TASK)]
)
def test_task_snapshots(command, response, respx_mock, snapshot):
    config.save_token("token")
    respx_mock.get(f"{BASE}/tasks" + ("/1" if "show" in command else "")).respond(
        200, json=response
    )
    assert runner.invoke(main.app, command).output == snapshot


def test_network_and_json_errors(respx_mock):
    route = respx_mock.get(f"{BASE}/tasks")
    route.mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(api_client.APIError, match="Can't reach"):
        api_client.get_all_task("token")
    route.respond(200, text="broken")
    with pytest.raises(api_client.APIError, match="invalid JSON"):
        api_client.get_all_task("token")


def test_config_corrupt_and_username():
    config.CONFIG_FILE.write_text("not json")
    assert config.load_token() is None
    for token in ["invalid", "a.!!!.c", "a.eyJzdWIiOiJhbGljZSJ9.c"]:
        config.save_token(token)
        assert config.get_logged_in_username() == ("alice" if token.startswith("a.ey") else None)
    assert "alice" in runner.invoke(main.app, []).output
    config.delete_token()
    config.delete_token()


def test_interactive_tasks(prompts, respx_mock):
    config.save_token("token")
    get = respx_mock.get(f"{BASE}/tasks/1").respond(200, json=TASK)
    put = respx_mock.put(f"{BASE}/tasks/1").respond(200, json=TASK)
    post = respx_mock.post(f"{BASE}/tasks").respond(201, json=TASK)
    prompts("new title", "new description", True)
    assert runner.invoke(main.app, ["task", "update", "1"]).exit_code == 0
    assert json.loads(put.calls.last.request.content)["is_completed"] is True
    prompts(None, "description", False)
    assert runner.invoke(main.app, ["task", "update", "1"]).exit_code == 0
    prompts("title", "description")
    assert runner.invoke(main.app, ["task", "create"]).exit_code == 0
    assert post.called and get.called
    prompts(None)
    assert runner.invoke(main.app, ["task", "create"]).exit_code == 0
    prompts("title", None)
    assert runner.invoke(main.app, ["task", "create"]).exit_code == 0
    prompts(False)
    assert "Cancelled" in runner.invoke(main.app, ["task", "delete", "1"]).output


def test_empty_list(respx_mock):
    config.save_token("token")
    respx_mock.get(f"{BASE}/tasks").respond(200, json=[])
    assert "No tasks" in runner.invoke(main.app, ["task", "list"]).output


def test_scaffold_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from cli.services import scaffold

    monkeypatch.setattr(scaffold.subprocess, "run", Mock())
    assert runner.invoke(main.app, ["init", "create", "python", "demo"]).exit_code == 0
    assert (tmp_path / "demo" / "main.py").is_file()
    assert runner.invoke(main.app, ["init", "create", "missing", "demo"]).exit_code == 1
    assert runner.invoke(main.app, ["init", "create", "python", "../escape"]).exit_code == 1
