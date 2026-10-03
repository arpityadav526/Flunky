import asyncio

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Footer, Header, Input, Static

from cli import offline
from cli.api_client import APIError


class TaskBoard(App[None]):
    """Keyboard and mouse task board; shared services preserve CLI semantics."""

    CSS = "DataTable { width: 65%; } #detail { width: 35%; padding: 1 2; } Input { margin: 1; }"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("d", "complete", "Complete"),
        ("u", "undo", "Undo"),
        ("/", "search", "Search"),
        ("escape", "task_list", "Task list"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search tasks…", id="search")
        with Horizontal():
            yield DataTable(id="tasks", cursor_type="row")
            yield Static("Select a task to view details.", id="detail")
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("ID", "Title", "Priority", "Due", "Status")
        await self.action_refresh()
        self.query_one(DataTable).focus()

    async def action_refresh(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        try:
            rows, cached = await asyncio.to_thread(
                offline.list_tasks, search=self.query_one(Input).value, limit=100
            )
            self.title = "Flunky · offline" if cached else "Flunky"
            for row in rows:
                table.add_row(
                    str(row["id"]),
                    row["title"],
                    row.get("priority", "medium"),
                    str(row.get("due_date") or "—"),
                    "done" if row.get("is_completed") else "open",
                    key=str(row["id"]),
                )
        except (ValueError, RuntimeError, APIError) as exc:
            self.notify(str(exc), severity="error")

    async def on_input_changed(self, event: Input.Changed) -> None:
        await self.action_refresh()

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key.value:
            try:
                row, _ = await asyncio.to_thread(offline.get_task, int(event.row_key.value))
                self.query_one("#detail", Static).update(
                    f"{row['title']}\n\n{row.get('notes') or row.get('description') or 'No notes'}"
                )
            except (ValueError, APIError) as exc:
                self.notify(str(exc), severity="error")

    async def action_complete(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count:
            task_id = int(str(table.get_row_at(table.cursor_row)[0]))
            try:
                await asyncio.to_thread(offline.mutate, task_id, {"is_completed": True})
                await self.action_refresh()
            except (ValueError, APIError) as exc:
                self.notify(str(exc), severity="error")

    async def action_undo(self) -> None:
        try:
            await asyncio.to_thread(offline.undo)
            await self.action_refresh()
        except (ValueError, APIError) as exc:
            self.notify(str(exc), severity="warning")

    def action_search(self) -> None:
        self.query_one(Input).focus()

    def action_task_list(self) -> None:
        self.query_one(DataTable).focus()
