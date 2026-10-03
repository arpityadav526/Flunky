from typing import Any

import typer
from rich.panel import Panel
from rich.table import Table

from cli import ui
from cli.ai import app as ai_app
from cli.api_client import (
    delete_task as api_delete_task,
)
from cli.api_client import (
    get_all_task,
    get_task_by_id,
    login_user,
    register_user,
)
from cli.api_client import (
    task_func as api_task_create,
)
from cli.api_client import (
    update_task as api_update_task,
)
from cli.blueprints.commands import register_blueprints
from cli.commands import register_commands
from cli.config import (
    delete_token,
    get_logged_in_username,
    is_locked_in_lmao,
    load_token,
    save_token,
)
from cli.services.projects import (
    add_project,
    list_projects,
    remove_project,
)
from cli.ui.commands import FlunkyGroup
from cli.ui.prompts import questionary
from cli.ui_theme import console

app = typer.Typer(
    cls=FlunkyGroup,
    help="[bold blue]FLUNKY[/bold blue] - [green]Developer Productivity CLI[/green]",
)
task_app = typer.Typer(cls=FlunkyGroup, help="[yellow]Commands for task management[/yellow]")
projects_app = typer.Typer(
    cls=FlunkyGroup, help="[magenta]Commands for project shortcuts[/magenta]"
)

app.add_typer(task_app, name="task")
app.add_typer(projects_app, name="projects")
register_blueprints(app)

app.add_typer(ai_app, name="ai", hidden=True)


@app.command()
def register(
    username: str | None = typer.Option(None, "--username", "-u"),
    email: str | None = typer.Option(None, "--email"),
    password_stdin: bool = typer.Option(False, "--password-stdin"),
):
    """Create an account. Example: flunky register -u alice --email a@example.com --password-stdin."""
    console.print(Panel.fit("📝 User Registration"))

    username = (
        username
        or questionary.text(
            "Username:",
            validate=lambda text: (
                True if len(text) >= 3 else "Username must be at least 3 characters"
            ),
        ).ask()
    )
    if not username:
        return

    import re

    email = (
        email
        or questionary.text(
            "E-mail:",
            validate=lambda text: (
                True if re.match(r"[^@]+@[^@]+\.[^@]+", text) else "Invalid email address"
            ),
        ).ask()
    )
    if not email:
        return

    if password_stdin:
        import sys

        password = sys.stdin.readline().rstrip("\r\n")
        if not password:
            raise ValueError("Password stdin was empty.")
    else:
        password = questionary.password(
            "Password:",
            validate=lambda text: (
                True if len(text) >= 6 else "Password must be at least 6 characters"
            ),
        ).ask()
        if not password:
            return

        password2 = questionary.password(
            "Confirm Password:",
            validate=lambda text: True if text == password else "Passwords do not match",
        ).ask()
        if not password2:
            return

    with console.status("[bold green]Registering..."):
        try:
            user = register_user(username, email, password)
            ui.state.data = {"user": user}
            console.print(
                f"✅ Registration successful. Welcome, {user['username']}!", style="green"
            )
        except Exception as e:
            if ui.state.debug:
                raise
            msg = str(e)
            if "already exists" in msg:
                console.print("[red]Username or email already registered.[/red]")
            else:
                console.print(f"❌ Registration failed: {msg}", style="red")

            raise typer.Exit(1) from None


@app.command()
def login(
    with_password: bool = typer.Option(
        False, "--with-password", help="Use password login instead of browser approval"
    ),
    username: str | None = typer.Option(None, "--username", "-u"),
    password_stdin: bool = typer.Option(False, "--password-stdin", help="Read password from stdin"),
):
    """Sign in via browser. Scripts: flunky login --with-password -u alice --password-stdin."""
    import sys
    import time
    import webbrowser

    from cli.api_client import APIError, _request

    try:
        if with_password:
            username = username or questionary.text("Username:").ask()
            if not username:
                return
            password = (
                sys.stdin.readline().rstrip("\r\n")
                if password_stdin
                else questionary.password("Password:").ask()
            )
            if not password:
                return
            result = login_user(username, password)
        else:
            result = _request("POST", "/v1/auth/device")
            console.print(
                Panel(
                    f"Open {result['verification_uri']}\nEnter code: [bold]{result['user_code']}[/bold]",
                    title="Sign in to Flunky",
                )
            )
            webbrowser.open(result["verification_uri"])
            deadline = time.monotonic() + result["expires_in"]
            interval = result["interval"]
            device_code = result["device_code"]
            while time.monotonic() < deadline:
                time.sleep(interval)
                try:
                    result = _request(
                        "POST", "/v1/auth/device/token", payload={"device_code": device_code}
                    )
                    break
                except APIError as error:
                    if str(error) == "authorization_pending":
                        continue
                    if error.status_code == 429:
                        interval += 5
                        continue
                    raise
            else:
                raise APIError("Device code expired. Run `flunky login` again.")
        save_token(result["access_token"], result.get("refresh_token"))
        ui.state.data = {"authenticated": True}
        console.print("Login successful.", style="success")
    except (APIError, OSError) as error:
        console.print(f"Login failed: {error}", style="error")
        raise typer.Exit(1) from None
    except (KeyboardInterrupt, EOFError):
        console.print("Sign-in cancelled.", style="warning")
        raise typer.Exit(130) from None


@app.command()
def logout(
    everywhere: bool = typer.Option(
        False, "--everywhere", help="Revoke every session and automation token"
    ),
):
    """Revoke the current session on the server and remove local credentials."""
    from cli.api_client import APIError, _request

    token = load_token()
    if not token:
        console.print("You're not logged in!", style="warning")
        return
    try:
        _request("POST", "/v1/auth/logout", token=token, params={"everywhere": everywhere})
    except APIError as error:
        if error.status_code != 401:
            console.print(
                f"Logout failed: {error}. Credentials retained so you can retry.", style="error"
            )
            raise typer.Exit(1) from None
    delete_token()
    ui.state.data = {"authenticated": False}
    console.print("Logged out successfully!", style="success")


@task_app.command("create")
def create_task_command(
    title: str | None = typer.Option(None, "--title", "-t", help="Task title"),
    description: str | None = typer.Option(None, "--description", "-d", help="Task description"),
):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        console.print("Run: flunky login", style="yellow")
        raise typer.Exit(1)

    if title is None:
        title = questionary.text("Set the Title:").ask()
        if not title:
            return

    if description is None:
        description = questionary.text("Write a description:", default="").ask()
        if description is None:
            return

    try:
        token = load_token()
        assert token is not None
        task = api_task_create(title, description, token)
        ui.state.data = task
        console.print("✅ Task created successfully!", style="green")
        console.print(f"ID: {task['id']} | Title: {task['title']}", style="cyan")
    except Exception as e:
        if ui.state.debug:
            raise
        msg = str(e)
        if "expired" in msg or "token" in msg:
            console.print("[red]Session expired. Please login again.[/red]")
        else:
            console.print(f"❌ Failed to create task: {msg}", style="red")

        raise typer.Exit(1) from None


@task_app.command("list")
def list_task(
    completed: bool | None = typer.Option(None, "--completed", help="Filter by completion status"),
):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        raise typer.Exit(1)

    try:
        token = load_token()
        assert token is not None
        tasks = get_all_task(token, completed=completed)
        ui.state.data = tasks

        if not tasks:
            console.print("📭 No tasks found!", style="yellow")
            return

        table = Table(title="Your Tasks", show_header=True, header_style="highlight")
        table.add_column("ID", style="info", width=6)
        table.add_column("Title", style="white", width=30)
        table.add_column("Description", style="dim", width=40)
        table.add_column("Status", style="success", width=12)

        for task in tasks:
            status = "✅ Done" if task["is_completed"] else "⏳ Pending"
            status_style = "success" if task["is_completed"] else "warning"

            table.add_row(
                str(task["id"]),
                task["title"],
                task.get("description") or "-",
                f"[{status_style}]{status}[/{status_style}]",
            )

        console.print(table)
        console.print(f"\nTotal: {len(tasks)} task(s)", style="dim")

    except Exception as e:
        if ui.state.debug:
            raise
        msg = str(e)
        if "expired" in msg or "token" in msg:
            console.print("[red]Session expired. Please login again.[/red]")
        else:
            console.print(f"❌ Failed to get tasks: {msg}", style="red")

        raise typer.Exit(1) from None


@task_app.command("show")
def show_task(task_id: int = typer.Argument(..., help="Task ID to show")):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        raise typer.Exit(1)

    try:
        token = load_token()
        assert token is not None
        task = get_task_by_id(task_id, token)
        ui.state.data = task

        status = "✅ Completed" if task["is_completed"] else "⏳ Pending"
        status_color = "green" if task["is_completed"] else "yellow"

        details = f"""
[bold cyan]ID:[/bold cyan] {task["id"]}
[bold cyan]Title:[/bold cyan] {task["title"]}
[bold cyan]Description:[/bold cyan] {task.get("description") or "No description"}
[bold cyan]Status:[/bold cyan] [{status_color}]{status}[/{status_color}]
[bold cyan]Created:[/bold cyan] {task["created_at"]}
"""
        console.print(Panel(details.strip(), title="📝 Task Details", border_style="cyan"))
    except Exception as e:
        if ui.state.debug:
            raise
        console.print(f"❌ Failed to get task: {e}", style="red")

        raise typer.Exit(1) from None


@task_app.command("update")
def update_task_command(
    task_id: int = typer.Argument(..., help="Task ID to update"),
    title: str | None = typer.Option(None, "--title", "-t", help="New title"),
    description: str | None = typer.Option(None, "--description", "-d", help="New description"),
    completed: bool | None = typer.Option(None, "--completed", "-c", help="Mark as completed"),
):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        raise typer.Exit(1)

    try:
        token = load_token()
        assert token is not None

        if title is None and description is None and completed is None:
            current_task = get_task_by_id(task_id, token)

            console.print(f"\n[bold]Updating task: {current_task['title']}[/bold]")
            console.print("[dim]Leave blank to keep current value[/dim]\n")

            new_title = questionary.text("New title:", default=current_task["title"]).ask()
            new_description = questionary.text(
                "New description:", default=current_task.get("description") or ""
            ).ask()
            mark_complete = questionary.confirm(
                "Mark as complete?", default=current_task["is_completed"]
            ).ask()

            if new_title is None or new_description is None or mark_complete is None:
                return

            title = new_title if new_title != current_task["title"] else None
            description = (
                new_description
                if new_description != (current_task.get("description") or "")
                else None
            )
            completed = mark_complete if mark_complete != current_task["is_completed"] else None

        updated_task = api_update_task(
            task_id,
            token,
            title=title,
            description=description,
            is_completed=completed,
        )

        console.print("✅ Task updated successfully!", style="green")
        console.print(f"Title: {updated_task['title']}", style="cyan")
    except Exception as e:
        if ui.state.debug:
            raise
        console.print(f"❌ Failed to update task: {e}", style="red")

        raise typer.Exit(1) from None


@task_app.command("complete")
def complete_task(task_id: int = typer.Argument(..., help="Task ID to mark as complete")):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        raise typer.Exit(1)

    try:
        token = load_token()
        assert token is not None
        updated_task = api_update_task(task_id, token, is_completed=True)
        console.print(f"✅ Task '{updated_task['title']}' marked as complete!", style="green")
    except Exception as e:
        if ui.state.debug:
            raise
        console.print(f"❌ Failed to complete task: {e!s}", style="red")

        raise typer.Exit(1) from None


@task_app.command("delete")
def delete_task_command(
    task_id: int = typer.Argument(..., help="Task ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        raise typer.Exit(1)

    try:
        token = load_token()
        assert token is not None
        task = get_task_by_id(task_id, token)
        ui.state.data = task

        if not force:
            if not questionary.confirm(f"⚠️ Delete '{task['title']}'?", default=False).ask():
                console.print("Cancelled.", style="warning")
                return

        api_delete_task(task_id, token)
        ui.state.data = {"deleted": task_id}
        console.print("🗑️ Task deleted successfully!", style="green")
    except Exception as e:
        if ui.state.debug:
            raise
        console.print(f"❌ Failed to delete task: {e}", style="red")

        raise typer.Exit(1) from None


@projects_app.command("add")
def add_project_command(name: str, path: str):
    try:
        project_name, project_path = add_project(name, path)
        console.print(
            f"✅ Added project '[bold]{project_name}[/bold]' → {project_path}", style="green"
        )
    except Exception as e:
        if ui.state.debug:
            raise
        msg = str(e)
        if "invalid" in msg:
            console.print(f"[red]Invalid project name or path: {msg}")
        else:
            console.print(f"❌ {msg}", style="red")

        raise typer.Exit(1) from None


@projects_app.command("list")
def list_projects_command():
    try:
        projects = list_projects()
        ui.state.data = projects

        if not projects:
            console.print(
                Panel("No saved projects found.", title="📁 Projects", border_style="yellow")
            )
            return

        table = Table(
            title="[bold magenta]Saved Projects[/bold magenta]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Name", style="cyan", justify="right")
        table.add_column("Path", style="magenta")

        for name, path in projects.items():
            icon = "📁"
            table.add_row(f"{icon} {name}", path)

        console.print(table)
    except Exception as e:
        if ui.state.debug:
            raise
        console.print(Panel(f"❌ {e}", title="Error", border_style="red"))

        raise typer.Exit(1) from None


@projects_app.command("remove")
def remove_project_command(name: str):
    try:
        removed = remove_project(name)
        console.print(f"🗑️ Removed project '[bold]{removed}[/bold]'", style="green")
    except Exception as e:
        if ui.state.debug:
            raise
        console.print(Panel(f"❌ {e}", title="Error", border_style="red"))

        raise typer.Exit(1) from None


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress normal output"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable color"),
    yes: bool = typer.Option(False, "--yes", help="Confirm prompts"),
    debug: bool = typer.Option(False, "--debug", help="Show tracebacks"),
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show version"),
):
    """
    [bold blue]FLUNKY[/bold blue] - [green]Developer Productivity CLI[/green]
    """
    if version:
        from importlib.metadata import version as package_version

        console.print(f"flunky {package_version('flunky')}")
        raise typer.Exit()

    from cli.updatecheck import notify

    notify()

    if ctx.invoked_subcommand is not None:
        return

    banner = """[bold cyan]
███████╗██╗     ██╗   ██╗███╗   ██╗██╗  ██╗██╗   ██╗
██╔════╝██║     ██║   ██║████╗  ██║██║ ██╔╝╚██╗ ██╔╝
█████╗  ██║     ██║   ██║██╔██╗ ██║█████╔╝  ╚████╔╝ 
██╔══╝  ██║     ██║   ██║██║╚██╗██║██╔═██╗   ╚██╔╝  
██║     ███████╗╚██████╔╝██║ ╚████║██║  ██╗   ██║   
╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   
[/bold cyan]"""

    console.print(banner)

    username = get_logged_in_username()
    if username:
        auth_status = (
            f"[bold green]● Locked in as:[/bold green] [bold white]{username}[/bold white] 🔓"
        )
    else:
        auth_status = (
            "[bold yellow]○ Not logged in[/bold yellow] 🔒 (Run [cyan]flunky login[/cyan])"
        )

    welcome_panel = Panel(
        f"{auth_status}\n\n"
        "[bold cyan]⚡ Quick Commands:[/bold cyan]\n"
        "  • [yellow]flunky init create <stack> <name>[/yellow]   - Scaffold a new project\n"
        "  • [yellow]flunky task list[/yellow]                 - Show your tasks\n"
        "  • [yellow]flunky task create[/yellow]               - Create a new task\n"
        "  • [yellow]flunky projects list[/yellow]             - View registered local projects\n\n"
        "[bold dim]Run any command with --help for options.[/bold dim]",
        title="[bold white]🚀 Welcome to FLUNKY[/bold white]",
        border_style="cyan",
        expand=False,
    )
    console.print(welcome_panel)
    dashboard: dict[str, Any] = {
        "username": username,
        "authenticated": bool(username),
        "today": [],
        "overdue": 0,
    }
    if username:
        try:
            from datetime import date

            from cli.offline import list_tasks as dashboard_tasks

            rows, cached = dashboard_tasks(completed=False, limit=100)
            today = date.today().isoformat()
            dashboard.update(
                today=[row for row in rows if row.get("due_date") == today],
                overdue=sum(1 for row in rows if row.get("due_date") and row["due_date"] < today),
                offline=cached,
            )
            console.print(
                f"Today: {len(dashboard['today'])} tasks · Overdue: {dashboard['overdue']}"
                + (" · offline" if cached else "")
            )
        except Exception:
            dashboard["offline"] = True
            console.print(
                "Tasks unavailable. Run `flunky doctor` to check the backend.", style="warning"
            )
    ui.state.data = dashboard


register_commands(app)

if __name__ == "__main__":
    app()
