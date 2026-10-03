"""Quick commands; heavyweight optional interfaces load only when requested."""

import os
import platform
import shutil
import sys
from datetime import date, timedelta
from typing import Any, Callable

import typer

from cli import offline, settings, ui
from cli.ui.commands import FlunkyGroup
from cli.ui.prompts import questionary


def due_date(value: str | None) -> str | None:
    if value is None:
        return None
    import dateparser

    parsed = dateparser.parse(
        value,
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": __import__("datetime").datetime.now(),
        },
    )
    if parsed is None:
        raise ValueError(f"Cannot parse date '{value}'. Try tomorrow or YYYY-MM-DD.")
    return parsed.date().isoformat()


def selected(task_id: int | None) -> int:
    if task_id is not None:
        return task_id
    rows, _ = offline.list_tasks(limit=100)
    choices = {f"{row['id']} · {row['title']}": row["id"] for row in rows}
    if not choices:
        raise ValueError('No tasks to select. Run `flunky add "your task"`.')
    choice = questionary.autocomplete("Task:", choices=list(choices), match_middle=True).ask()
    if choice not in choices:
        raise ValueError("No task selected. Pass a task ID to skip the picker.")
    return int(choices[choice])


def report(result: tuple[dict[str, Any], bool], message: str) -> None:
    task, cached = result
    ui.output(
        {**task, "offline": cached},
        ("[offline] " if cached else "") + message + f" (#{task['id']})",
    )


def add(
    title: str,
    priority: str = typer.Option("medium", "--priority", "-p"),
    due: str | None = typer.Option(None, "--due", "-d"),
    tags: list[str] | None = typer.Option(None, "--tag", "-t"),
    notes: str | None = typer.Option(None, "--notes"),
) -> None:
    """Quick-add a task. Example: flunky add 'fix login' -p high -d tomorrow -t backend."""
    if priority not in {"low", "medium", "high"} or not title.strip():
        raise ValueError("Use a non-empty title and priority low, medium, or high.")
    payload = {
        "task_title": title.strip(),
        "priority": priority,
        "due_date": due_date(due),
        "tags": tags or [],
        "notes": notes,
    }
    report(offline.add_task(payload), "Task created")


def list_tasks(
    completed: str | None = typer.Option(None, "--completed"),
    priority: str | None = typer.Option(None, "--priority", "-p"),
    tag: str | None = typer.Option(None, "--tag", "-t"),
    search: str | None = typer.Option(None, "--search", "-s"),
    sort: str = typer.Option("created_at", "--sort"),
    limit: int = typer.Option(50, min=1, max=100),
    offset: int = typer.Option(0, min=0),
    due_before: str | None = typer.Option(None),
    due_after: str | None = typer.Option(None),
) -> None:
    """Find tasks. Example: flunky list --search login --completed false --sort=-priority."""
    if completed not in {None, "true", "false"}:
        raise ValueError("--completed expects true or false.")
    if sort.lstrip("-") not in {"created_at", "updated_at", "title", "priority", "due_date"}:
        raise ValueError(
            "Sort by title, priority, due_date, created_at, or updated_at (prefix - to reverse)."
        )
    filters = {
        "completed": None if completed is None else completed == "true",
        "priority": priority,
        "tag": tag,
        "search": search,
        "sort": sort,
        "limit": limit,
        "offset": offset,
        "due_before": due_date(due_before),
        "due_after": due_date(due_after),
    }
    rows, cached = offline.list_tasks(
        **{key: value for key, value in filters.items() if value is not None}
    )
    ui.state.data = {"tasks": rows, "offline": cached, "offset": offset, "limit": limit}
    if cached:
        ui.console.print("[offline] Cached tasks; run flunky sync when connected.", markup=False)
    ui.output(rows)
    ui.state.data = {"tasks": rows, "offline": cached, "offset": offset, "limit": limit}


def today() -> None:
    """Show tasks due today. Example: flunky today --json."""
    rows, cached = offline.list_tasks(
        completed=False,
        due_before=date.today().isoformat(),
        due_after=date.today().isoformat(),
        limit=100,
    )
    ui.output(rows)
    ui.state.data = {"tasks": rows, "offline": cached}
    if cached:
        ui.console.print("[offline] Cached tasks", markup=False)


def upcoming() -> None:
    """Show future tasks. Example: flunky upcoming."""
    rows, cached = offline.list_tasks(
        completed=False,
        due_after=(date.today() + timedelta(days=1)).isoformat(),
        sort="due_date",
        limit=100,
    )
    ui.output(rows)
    ui.state.data = {"tasks": rows, "offline": cached}
    if cached:
        ui.console.print("[offline] Cached tasks", markup=False)


def show(task_id: int | None = typer.Argument(None)) -> None:
    """Inspect a task or choose one. Example: flunky show 42."""
    task, cached = offline.get_task(selected(task_id))
    ui.output({**task, "offline": cached})


def done(task_id: int | None = typer.Argument(None)) -> None:
    """Complete a task. Example: flunky done 42."""
    report(offline.mutate(selected(task_id), {"is_completed": True}), "Task completed")


def edit(
    task_id: int | None = typer.Argument(None),
    title: str | None = typer.Option(None, "--title"),
    priority: str | None = typer.Option(None, "--priority", "-p"),
    due: str | None = typer.Option(None, "--due", "-d"),
    notes: str | None = typer.Option(None, "--notes"),
    tags: list[str] | None = typer.Option(None, "--tag", "-t"),
) -> None:
    """Edit task fields. Example: flunky edit 42 --title 'ship release' -p high."""
    if priority is not None and priority not in {"low", "medium", "high"}:
        raise ValueError("Priority must be low, medium, or high.")
    payload = {
        key: value
        for key, value in {
            "title": title,
            "priority": priority,
            "due_date": due_date(due),
            "notes": notes,
            "tags": tags,
        }.items()
        if value is not None
    }
    if not payload:
        raise ValueError("Supply at least one field, such as --title or --priority.")
    report(offline.mutate(selected(task_id), payload), "Task updated")


def remove(
    task_id: int | None = typer.Argument(None), force: bool = typer.Option(False, "--force", "-f")
) -> None:
    """Soft-delete a task. Example: flunky rm 42 --yes; flunky undo restores it."""
    task_id = selected(task_id)
    if (
        not (force or ui.state.yes)
        and not questionary.confirm(f"Delete task {task_id}?", default=False).ask()
    ):
        ui.output({"cancelled": True}, "Cancelled.")
        return
    report(offline.mutate(task_id, {}, "delete"), "Task deleted")


def undo() -> None:
    """Undo the last deletion or edit. Example: flunky undo."""
    report(offline.undo(), "Last change undone")


def sync() -> None:
    """Send queued offline changes in order. Example: flunky sync --json."""
    result = offline.sync()
    ui.output(result, f"Synced {result['synced']} queued change(s).")


def doctor() -> None:
    """Check installation, backend, auth and terminal. Example: flunky doctor --json."""
    from importlib.metadata import version

    import keyring

    from cli import api_client, config

    result: dict[str, Any] = {
        "python": platform.python_version(),
        "flunky": version("flunky"),
        "platform": platform.system(),
        "api_url": settings.api_url(),
        "path": shutil.which("flunky"),
        "terminal": os.environ.get("TERM", "unknown"),
        "tty": sys.stdout.isatty(),
        "unicode": ui.unicode_supported(),
        "color": not ui.state.no_color,
        "keychain": keyring.get_keyring().priority > 0,
    }
    try:
        result["backend"] = api_client._request("GET", "/ready")
    except api_client.APIError as exc:
        result["backend"] = {"error": str(exc)}
    token = config.load_credentials().get("access_token")
    if token:
        try:
            result["auth"] = api_client._request("GET", "/v1/auth/me", token=token)["username"]
        except api_client.APIError as exc:
            result["auth"] = str(exc)
    else:
        result["auth"] = "not logged in"
    ui.output(result)
    if isinstance(result["backend"], dict) and "error" in result["backend"]:
        raise typer.Exit(1)


def tui() -> None:
    """Open the full-screen task board. Example: flunky tui (q to quit)."""
    if not sys.stdin.isatty() or not sys.stdout.isatty() or ui.state.json:
        raise ValueError(
            "The TUI needs an interactive terminal. Use `flunky list --json` in scripts."
        )
    from cli.tui import TaskBoard

    TaskBoard().run()


def register_commands(app: typer.Typer) -> None:
    callbacks: list[tuple[str, Callable[..., Any]]] = [
        ("add", add),
        ("list", list_tasks),
        ("today", today),
        ("upcoming", upcoming),
        ("show", show),
        ("done", done),
        ("edit", edit),
        ("rm", remove),
        ("undo", undo),
        ("sync", sync),
        ("doctor", doctor),
        ("tui", tui),
    ]
    for name, callback in callbacks:
        app.command(name)(callback)
    config_app = typer.Typer(
        cls=FlunkyGroup, help="Settings and profiles. Example: flunky config list."
    )
    app.add_typer(config_app, name="config")

    @config_app.command("list")
    def config_list() -> None:
        """Show settings. Example: flunky config list --json."""
        ui.output(settings.load())

    @config_app.command("get")
    def config_get(key: str) -> None:
        """Read a profile value. Example: flunky config get api_url."""
        config = settings.load()
        values = config["profiles"][config["active_profile"]]
        if key not in values:
            raise ValueError(f"Unknown setting: {key}")
        ui.output({key: values[key]})

    @config_app.command("set")
    def config_set(key: str, value: str) -> None:
        """Set api_url or theme. Example: flunky config set api_url http://localhost:8000."""
        if key not in {"api_url", "theme"}:
            raise ValueError("Supported settings: api_url, theme.")
        config = settings.load()
        config["profiles"][config["active_profile"]][key] = value
        settings.save(config)
        ui.output({key: value}, f"Saved {key}.")

    @config_app.command("profile")
    def profile(name: str) -> None:
        """Switch local/staging/prod profile. Example: flunky config profile staging."""
        config = settings.load()
        if name not in config["profiles"]:
            raise ValueError("Choose local, staging, or prod.")
        config["active_profile"] = name
        settings.save(config)
        ui.output({"profile": name}, f"Using profile {name}.")

    completion = typer.Typer(
        cls=FlunkyGroup, help="Shell completion. Example: flunky completion install zsh."
    )
    app.add_typer(completion, name="completion")

    @completion.command("install")
    def completion_install(shell: str = typer.Argument("zsh")) -> None:
        """Install shell completion. Example: flunky completion install zsh."""
        from typer._completion_shared import install

        if shell not in {"zsh", "bash", "fish", "powershell", "pwsh"}:
            raise ValueError("Choose zsh, bash, fish, powershell, or pwsh.")
        installed, path = install(shell=shell, prog_name="flunky")
        ui.output(
            {"shell": installed, "path": str(path)},
            f"Installed completion: {path}. Restart your shell.",
        )
