import typer
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from cli.config import delete_token, is_locked_in_lmao, load_token, save_token
from cli.api_client import (
    delete_task as api_delete_task,
    get_all_task,
    get_task_by_id,
    login_user,
    register_user,
    task_func as api_task_create,
    update_task as api_update_task,
)
from cli.services.projects import (
    add_project,
    get_project_path,
    list_projects,
    remove_project,
)
from cli.services.vscode import open_in_vscode

app = typer.Typer(help="FLUNKY - Developer Productivity CLI")
task_app = typer.Typer(help="Commands for task management")
projects_app = typer.Typer(help="Commands for project shortcuts")
init_app = typer.Typer(help="Commands for project scaffolding")
setup_app = typer.Typer(help="Commands for dependency and environment setup")
ai_app = typer.Typer(help="AI-assisted developer commands")

app.add_typer(task_app, name="task")
app.add_typer(projects_app, name="projects")
app.add_typer(init_app, name="init")
app.add_typer(setup_app, name="setup")
app.add_typer(ai_app, name="ai")

console = Console()


@app.command()
def register():
    console.print(Panel.fit("📝 User Registration"))

    username = Prompt.ask("Username")
    email = Prompt.ask("E-mail")
    password = Prompt.ask("Password", password=True)

    try:
        user = register_user(username, email, password)
        console.print(f"✅ Registration successful. Welcome, {user['username']}!", style="green")
    except Exception as e:
        console.print(f"❌ Registration failed: {e}", style="red")


@app.command()
def login():
    console.print(Panel.fit("🔐 User Login"))

    username = Prompt.ask("Username")
    password = Prompt.ask("Password", password=True)

    try:
        result = login_user(username, password)
        token = result["access_token"]
        save_token(token)
        console.print("✅ Login successful. Token saved.", style="green")
    except Exception as e:
        console.print(f"❌ Login failed: {e}", style="red")


@app.command()
def logout():
    if not is_locked_in_lmao():
        console.print("⚠️ You're not logged in!", style="yellow")
        return

    delete_token()
    console.print("👋 Logged out successfully!", style="green")


@task_app.command("create")
def create_task_command(
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Task title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Task description"),
):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        console.print("Run: python -m cli.main login", style="yellow")
        return

    if title is None:
        title = Prompt.ask("Set the Title")

    if description is None:
        description = Prompt.ask("Write a description", default="")

    try:
        token = load_token()
        task = api_task_create(title, description, token)
        console.print("✅ Task created successfully!", style="green")
        console.print(f"ID: {task['id']} | Title: {task['title']}", style="cyan")
    except Exception as e:
        console.print(f"❌ Failed to create task: {e}", style="red")


@task_app.command("list")
def list_task(
    completed: Optional[bool] = typer.Option(None, "--completed", help="Filter by completion status")
):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        return

    try:
        token = load_token()
        tasks = get_all_task(token, completed=completed)

        if not tasks:
            console.print("📭 No tasks found!", style="yellow")
            return

        table = Table(title="Your Tasks", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Title", style="white", width=30)
        table.add_column("Description", style="dim", width=40)
        table.add_column("Status", style="green", width=12)

        for task in tasks:
            status = "✅ Done" if task["is_completed"] else "⏳ Pending"
            status_style = "green" if task["is_completed"] else "yellow"

            table.add_row(
                str(task["id"]),
                task["title"],
                task.get("description") or "-",
                f"[{status_style}]{status}[/{status_style}]"
            )

        console.print(table)
        console.print(f"\nTotal: {len(tasks)} task(s)", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to get tasks: {str(e)}", style="red")


@task_app.command("show")
def show_task(task_id: int = typer.Argument(..., help="Task ID to show")):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        return

    try:
        token = load_token()
        task = get_task_by_id(task_id, token)

        status = "✅ Completed" if task["is_completed"] else "⏳ Pending"
        status_color = "green" if task["is_completed"] else "yellow"

        details = f"""
[bold cyan]ID:[/bold cyan] {task['id']}
[bold cyan]Title:[/bold cyan] {task['title']}
[bold cyan]Description:[/bold cyan] {task.get('description') or 'No description'}
[bold cyan]Status:[/bold cyan] [{status_color}]{status}[/{status_color}]
[bold cyan]Created:[/bold cyan] {task['created_at']}
"""
        console.print(Panel(details.strip(), title="📝 Task Details", border_style="cyan"))
    except Exception as e:
        console.print(f"❌ Failed to get task: {e}", style="red")


@task_app.command("update")
def update_task_command(
    task_id: int = typer.Argument(..., help="Task ID to update"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    completed: Optional[bool] = typer.Option(None, "--completed", "-c", help="Mark as completed"),
):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        return

    try:
        token = load_token()

        if title is None and description is None and completed is None:
            current_task = get_task_by_id(task_id, token)

            console.print(f"\n[bold]Updating task: {current_task['title']}[/bold]")
            console.print("[dim]Leave blank to keep current value[/dim]\n")

            new_title = Prompt.ask("New title", default=current_task["title"])
            new_description = Prompt.ask(
                "New description",
                default=current_task.get("description") or ""
            )
            mark_complete = Confirm.ask(
                "Mark as complete?",
                default=current_task["is_completed"]
            )

            title = new_title if new_title != current_task["title"] else None
            description = (
                new_description
                if new_description != (current_task.get("description") or "")
                else None
            )
            completed = (
                mark_complete
                if mark_complete != current_task["is_completed"]
                else None
            )

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
        console.print(f"❌ Failed to update task: {e}", style="red")


@task_app.command("complete")
def complete_task(task_id: int = typer.Argument(..., help="Task ID to mark as complete")):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        return

    try:
        token = load_token()
        updated_task = api_update_task(task_id, token, is_completed=True)
        console.print(f"✅ Task '{updated_task['title']}' marked as complete!", style="green")
    except Exception as e:
        console.print(f"❌ Failed to complete task: {str(e)}", style="red")


@task_app.command("delete")
def delete_task_command(
    task_id: int = typer.Argument(..., help="Task ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        return

    try:
        token = load_token()
        task = get_task_by_id(task_id, token)

        if not force:
            if not Confirm.ask(f"⚠️ Delete '{task['title']}'?", default=False):
                console.print("Cancelled.", style="yellow")
                return

        api_delete_task(task_id, token)
        console.print("🗑️ Task deleted successfully!", style="green")
    except Exception as e:
        console.print(f"❌ Failed to delete task: {e}", style="red")


@projects_app.command("add")
def add_project_command(name: str, path: str):
    try:
        project_name, project_path = add_project(name, path)
        console.print(f"✅ Added project '[bold]{project_name}[/bold]' → {project_path}", style="green")
    except Exception as e:
        console.print(f"❌ {e}", style="red")


@projects_app.command("list")
def list_projects_command():
    try:
        projects = list_projects()

        if not projects:
            console.print("⚠️ No saved projects found.", style="yellow")
            return

        table = Table(title="Saved Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Path", style="magenta")

        for name, path in projects.items():
            table.add_row(name, path)

        console.print(table)
    except Exception as e:
        console.print(f"❌ {e}", style="red")


@projects_app.command("remove")
def remove_project_command(name: str):
    try:
        removed_name = remove_project(name)
        console.print(f"🗑️ Removed project '{removed_name}'", style="green")
    except Exception as e:
        console.print(f"❌ {e}", style="red")


@app.command("open")
def open_project_command(name: str):
    try:
        project_path = get_project_path(name)
        open_in_vscode(project_path)
        console.print(f"🚀 Opened '{name}' in VS Code", style="green")
    except Exception as e:
        console.print(f"❌ {e}", style="red")


if __name__ == "__main__":
    app()