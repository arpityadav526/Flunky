import typer
from rich.console import Console
from rich.prompt import Prompt
from typing import Optional
from rich.panel import Panel

from cli.api_client import register_func
from cli.config import save_token, load_token
from cli.api_client import login_user
from cli.config import delete_token, is_locked_in_lmao
from rich.table import Table
from rich.prompt import Confirm
from cli.api_client import (
    task_func as api_task_create,
    get_all_task,
    get_task_by_id,
    update_task as api_update_task,
    delete_task as api_delete_task
)



## MAIN APP ##
app= typer.Typer(help="FLUNKY - MY TASK MANAGEMENT CLI")
console=Console()

## SUB-APP FOR TASKS ##
task_app=typer.Typer(help="commands for flunky")
app.add_typer(task_app,name="task")


## REGISTER COMMAND ##
@app.command()
def register():
    console.print(Panel.fit("📝 User Registration", style="bold blue"))
    username=Prompt.ask("Username")
    e_mail=Prompt.ask("E-mail")
    password=Prompt.ask("Password", password=True)
    try:
        user_data=register_func(username=username, e_mail=e_mail ,password=password)
        console.print(f"✅ Registered successfully! Welcome, {user_data['username']}!", style="green")
    except Exception as e:
        console.print(f"❌ Registration failed: {str(e)}", style="red")




## LOGIN COMMAND ##
@app.command()
def login():
    console.print(Panel.fit("🔐 User Login", style="bold green"))

    username=Prompt.ask("Username")
    password=Prompt.ask("Password", password=True)


    try:
    # Call the API and get token
        token = login_user(username, password)

    # Save token to config file
        save_token(token)

        console.print("✅ Logged in successfully!", style="green")

    except Exception as e:
        console.print(f"❌ Login failed: {str(e)}", style="red")



## LOGOUT COMMAND ##
@app.command()
def logout():

    if not is_locked_in_lmao():
        console.print("⚠️  You're not logged in!", style="yellow")
        return

    delete_token()
    console.print("👋 Logged out successfully!", style="yellow")




@task_app.command("create")
def create_task_command(
        title: Optional[str] = typer.Option(None, "--title", "-t", help="Task title"),
        description: Optional[str] = typer.Option(None, "--description", "-d", help="Task description")

):

    if not is_locked_in_lmao():
        console.print("please dude log in first")
        console.print("Run: flunky login", style="yellow")
        return

    if title is None:
        title=Prompt.ask("Set the Title")

    if description is None:
        description=Prompt.ask("Write a description",default=" ")

    try:
        token=load_token()
        task=api_task_create(description, title , token)
        console.print(f"\n✅ Task created successfully!", style="green")
        console.print(f"ID: {task['id']} | Title: {task['title']}", style="cyan")

    except Exception as e:
        console.print(f"❌ Failed to create task: {str(e)}", style="red")





@task_app.command("list")
def list_task(
        completed: Optional[bool] = typer.Option(None, "--completed", help="Filter by completion status")
):

    if is_locked_in_lmao is None:
        console.print("please dude log in first!", style="red")
        return

    try:
        token=load_token()
        tasks=get_all_task(token , completed=True)


        if not tasks:
            console.print("📭 No tasks found!", style="yellow")


            table=Table(title="Your Tasks", show_header=True, header_style="bold-magenta")
            table.add_column("ID", style="cyan", width=6)
            table.add_column("Title", style="white", width=30)
            table.add_column("Description", style="dim", width=40)
            table.add_column("Status", style="green", width=12)

        for task in tasks:
            status="✅ Done" if task['is_completed'] else "⏳ Pending"
            status_style="green" if task['is_completed'] else "yellow"

            table.add_row(
            str(task['id']),
                task['title'],
                task['description'] or "-",
                f"[{status_style}]{status}[/{status_style}]"
            )
        console.print("\n")
        console.print(table)
        console.print(f"\nTotal: {len(tasks)} task(s)\n", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to get tasks: {str(e)}", style="red")




@task_app.command("show")
def show_task(task_id: int =typer.Argument(... , help="Task ID to show")):

    if not is_locked_in_lmao:
        console.print("❌ Please login first!", style="red")
        return

    try:
        token = load_token()
        task = get_task_by_id(task_id, token)

        # Create a panel with task details
        status = "✅ Completed" if task['is_completed'] else "⏳ Pending"
        status_color = "green" if task['is_completed'] else "yellow"

        details=f"""
        [bold cyan]ID:[/bold cyan] {task['id']}
[bold cyan]Title:[/bold cyan] {task['title']}
[bold cyan]Description:[/bold cyan] {task['description'] or 'No description'}
[bold cyan]Status:[/bold cyan] [{status_color}]{status}[/{status_color}]
[bold cyan]Created:[/bold cyan] {task['created_at']}
"""
        console.print(Panel(details.strip(), title="📝 Task Details", border_style="cyan"))

    except Exception as e:
        console.print(f"❌ Failed to get task: {str(e)}", style="red")


@task_app.command("update")
def update_task_command(
        task_id: int = typer.Argument(..., help="Task ID to update"),
        title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
        description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
        completed: Optional[bool] = typer.Option(None, "--completed", "-c", help="Mark as completed")
):

    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        return

    try:
        token = load_token()

        # If no args provided, get current task and prompt
        if title is None and description is None and completed is None:
            # Get current task
            current_task = get_task_by_id(task_id, token)

            console.print(f"\n[bold]Updating task: {current_task['title']}[/bold]")
            console.print("[dim]Leave blank to keep current value[/dim]\n")

            # Prompt for new values
            new_title = Prompt.ask("New title", default=current_task['title'])
            new_description = Prompt.ask("New description", default=current_task['description'] or "")
            mark_complete = Confirm.ask("Mark as complete?", default=current_task['is_completed'])

            # Use prompted values
            title = new_title if new_title != current_task['title'] else None
            description = new_description if new_description != (current_task['description'] or "") else None
            completed = mark_complete if mark_complete != current_task['is_completed'] else None

        # Update task
        updated_task = api_update_task(task_id, token, is_completed=True)


        console.print(f"\n✅ Task updated successfully!", style="green")
        console.print(f"Title: {updated_task['title']}", style="cyan")

    except Exception as e:
        console.print(f"❌ Failed to update task: {str(e)}", style="red")



@task_app.command("complete")
def complete_task(task_id: int =typer.Argument(... , help="Task ID to mark as complete")):

    if is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        return

    try:
        token=load_token()
        updated_task=api_update_task(token , task_id, is_completed=True)
        console.print(f"✅ Task '{updated_task['title']}' marked as complete!", style="green")


    except Exception as e:
        console.print(f"❌ Failed to complete task: {str(e)}", style="red")


@task_app.command("delete")
def delete_task_command(
        task_id: int = typer.Argument(..., help="Task ID to delete"),
        force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):


    if not is_locked_in_lmao():
        console.print("❌ Please login first!", style="red")
        return

    try:
        token = load_token()

        # Get task details for confirmation
        task = get_task_by_id(task_id, token)

        # Confirm deletion (unless --force)
        if not force:
            if not Confirm.ask(f"⚠️  Delete '{task['title']}'?", default=False):
                console.print("Cancelled.", style="yellow")
                return

        # Delete task
        api_delete_task(task_id, token)

        console.print(f"🗑️  Task deleted successfully!", style="green")

    except Exception as e:
        console.print(f"❌ Failed to delete task: {str(e)}", style="red")


if __name__=="__main__":
    app()


