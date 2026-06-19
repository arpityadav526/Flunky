import typer
from typing import Optional
import questionary

from rich.panel import Panel
from rich.table import Table

from cli.config import delete_token, get_logged_in_username, is_locked_in_lmao, load_token, save_token
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
    list_projects,
    remove_project,
)
from cli.services import scaffold
from cli.utils import validators
from cli.ui_theme import console


STACK_ICONS = {
    "fastapi": "⚡",
    "mern": "🌱",
    "cli": "💻",
    "python": "🐍",
    "ds": "📊",
    "react-native": "📱",
    "flutter": "🦋",
    "nextjs": "⏭️",
    "nestjs": "🚀",
    "electron": "🖥️",
}

app = typer.Typer(help="[bold blue]FLUNKY[/bold blue] - [green]Developer Productivity CLI[/green]")
task_app = typer.Typer(help="[yellow]Commands for task management[/yellow]")
projects_app = typer.Typer(help="[magenta]Commands for project shortcuts[/magenta]")
init_app = typer.Typer(help="[cyan]Commands for project scaffolding[/cyan]")
setup_app = typer.Typer(help="[blue]Commands for dependency and environment setup[/blue]")
ai_app = typer.Typer(help="[bold]AI-assisted developer commands[/bold]")

app.add_typer(task_app, name="task")
app.add_typer(projects_app, name="projects")
app.add_typer(init_app, name="init")
app.add_typer(setup_app, name="setup")
app.add_typer(ai_app, name="ai")

# console is imported from cli.ui_theme
# --- Project Scaffolding ---
@init_app.command("create")
def create_project(
    project_type: str = typer.Argument(..., help="Type of project to create (e.g. fastapi, mern, cli, ds, nextjs, etc.)"),
    project_name: str = typer.Argument(..., help="Name of the new project")
):
    """Create a new project from a template."""
    icon = STACK_ICONS.get(project_type, "📦")
    if not validators.is_valid_project_name(project_name):
        console.print(Panel(f"[red]Invalid project name: {project_name}[/red]", title="❌ Error", border_style="red"))
        raise typer.Exit(1)
    try:
        with console.status(f"[bold green]Scaffolding {icon} {project_type} project...[/bold green]"):
            path = scaffold.scaffold_project(project_type, project_name)
        console.print(Panel(f"{icon} [green]Project created at [bold]{path}[/bold][/green]", title="✅ Success", border_style="green"))
    except Exception as e:
        console.print(Panel(f"[red]{e}[/red]", title="❌ Error", border_style="red"))
        raise typer.Exit(1)


@app.command()
def register():
    console.print(Panel.fit("📝 User Registration"))

    username = questionary.text("Username:", validate=lambda text: True if len(text) >= 3 else "Username must be at least 3 characters").ask()
    if not username: return

    import re
    email = questionary.text("E-mail:", validate=lambda text: True if re.match(r"[^@]+@[^@]+\.[^@]+", text) else "Invalid email address").ask()
    if not email: return

    password = questionary.password("Password:", validate=lambda text: True if len(text) >= 6 else "Password must be at least 6 characters").ask()
    if not password: return

    password2 = questionary.password("Confirm Password:", validate=lambda text: True if text == password else "Passwords do not match").ask()
    if not password2: return

    with console.status("[bold green]Registering..."):
        try:
            user = register_user(username, email, password)
            console.print(f"✅ Registration successful. Welcome, {user['username']}!", style="green")
        except Exception as e:
            msg = str(e)
            if "already exists" in msg:
                console.print("[red]Username or email already registered.[/red]")
            else:
                console.print(f"❌ Registration failed: {msg}", style="red")


@app.command()
def login():
    console.print(Panel.fit("🔐 User Login"))

    username = questionary.text("Username:").ask()
    if not username: return
    password = questionary.password("Password:").ask()
    if not password: return

    with console.status("[bold green]Logging in..."):
        try:
            result = login_user(username, password)
            token = result["access_token"]
            save_token(token)
            console.print("✅ Login successful. Token saved.", style="green")
        except Exception as e:
            msg = str(e)
            if "401" in msg or "invalid" in msg:
                console.print("[red]Invalid username or password.[/red]")
            else:
                console.print(f"❌ Login failed: {msg}", style="red")


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
        title = questionary.text("Set the Title:").ask()
        if not title: return

    if description is None:
        description = questionary.text("Write a description:", default="").ask()
        if description is None: return

    try:
        token = load_token()
        task = api_task_create(title, description, token)
        console.print("✅ Task created successfully!", style="green")
        console.print(f"ID: {task['id']} | Title: {task['title']}", style="cyan")
    except Exception as e:
        msg = str(e)
        if "expired" in msg or "token" in msg:
            console.print("[red]Session expired. Please login again.[/red]")
        else:
            console.print(f"❌ Failed to create task: {msg}", style="red")


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
                f"[{status_style}]{status}[/{status_style}]"
            )

        console.print(table)
        console.print(f"\nTotal: {len(tasks)} task(s)", style="dim")

    except Exception as e:
        msg = str(e)
        if "expired" in msg or "token" in msg:
            console.print("[red]Session expired. Please login again.[/red]")
        else:
            console.print(f"❌ Failed to get tasks: {msg}", style="red")


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

            new_title = questionary.text("New title:", default=current_task["title"]).ask()
            new_description = questionary.text(
                "New description:",
                default=current_task.get("description") or ""
            ).ask()
            mark_complete = questionary.confirm(
                "Mark as complete?",
                default=current_task["is_completed"]
            ).ask()
            
            if new_title is None or new_description is None or mark_complete is None:
                raise typer.Exit()

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
            if not questionary.confirm(f"⚠️ Delete '{task['title']}'?", default=False).ask():
                console.print("Cancelled.", style="warning")
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
        msg = str(e)
        if "invalid" in msg:
            console.print(f"[red]Invalid project name or path: {msg}")
        else:
            console.print(f"❌ {msg}", style="red")


@projects_app.command("list")
def list_projects_command():
    try:
        projects = list_projects()

        if not projects:
            console.print(Panel("No saved projects found.", title="📁 Projects", border_style="yellow"))
            return

        table = Table(title="[bold magenta]Saved Projects[/bold magenta]", show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", justify="right")
        table.add_column("Path", style="magenta")

        for name, path in projects.items():
            icon = "📁"
            table.add_row(f"{icon} {name}", path)

        console.print(table)
    except Exception as e:
        console.print(Panel(f"❌ {e}", title="Error", border_style="red"))


@projects_app.command("remove")
def remove_project_command(name: str):
    try:
        removed = remove_project(name)
        console.print(f"🗑️ Removed project '[bold]{removed}[/bold]'", style="green")
    except Exception as e:
        console.print(Panel(f"❌ {e}", title="Error", border_style="red"))


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    [bold blue]FLUNKY[/bold blue] - [green]Developer Productivity CLI[/green]
    """
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
        auth_status = f"[bold green]● Locked in as:[/bold green] [bold white]{username}[/bold white] 🔓"
    else:
        auth_status = "[bold yellow]○ Not logged in[/bold yellow] 🔒 (Run [cyan]flunky login[/cyan])"

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
        expand=False
    )
    console.print(welcome_panel)


if __name__ == "__main__":
    app()