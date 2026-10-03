"""One output boundary for human, JSON, quiet, and non-TTY execution."""

import os
import sys
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any, ContextManager

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

DOCS = "https://github.com/arpityadav526/Flunky#readme"
THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "prompt": "magenta",
        "highlight": "bold magenta",
        "banner": "bold cyan",
    }
)


@dataclass
class OutputState:
    json: bool = False
    quiet: bool = False
    yes: bool = False
    debug: bool = False
    no_color: bool = False
    data: Any = None
    messages: list[str] = field(default_factory=list)
    failed: bool = False


state = OutputState()


def configure(flags: set[str]) -> None:
    global state
    state = OutputState(
        json="--json" in flags,
        quiet="--quiet" in flags,
        yes="--yes" in flags,
        debug="--debug" in flags,
        no_color="--no-color" in flags or "NO_COLOR" in os.environ,
    )
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")


def get_console(*, error: bool = False) -> Console:
    force = bool(os.environ.get("FORCE_COLOR")) and not state.no_color
    from cli import settings

    try:
        config = settings.load()
        chosen_theme = config["profiles"][config["active_profile"]].get("theme", "auto")
    except (ValueError, KeyError):
        chosen_theme = "auto"
    light = os.environ.get("COLORFGBG", "").split(";")[-1] in {"7", "15"}
    theme = THEME
    if os.environ.get("FLUNKY_THEME", chosen_theme) == "high-contrast":
        theme = Theme(
            {
                name: "bold"
                for name in ("info", "warning", "error", "success", "prompt", "highlight", "banner")
            }
        )
    elif chosen_theme == "light" or (chosen_theme == "auto" and light):
        theme = Theme(
            {
                "info": "blue",
                "warning": "dark_orange",
                "error": "bold red",
                "success": "green",
                "highlight": "magenta",
                "banner": "blue",
            }
        )
    return Console(
        stderr=error,
        theme=theme,
        no_color=state.no_color,
        force_terminal=force or None,
        color_system=None if state.no_color else "auto",
        markup=True,
        highlight=False,
    )


class UIConsole:
    def print(self, *objects: Any, **kwargs: Any) -> None:
        if state.json or state.quiet:
            from io import StringIO

            buffer = StringIO()
            Console(file=buffer, theme=THEME, color_system=None, width=100).print(
                *objects, **kwargs
            )
            state.messages.append(buffer.getvalue().strip())
        elif not state.quiet:
            if not unicode_supported():
                from io import StringIO

                from cli.fast_output import write

                buffer = StringIO()
                Console(
                    file=buffer, theme=THEME, color_system=None, width=get_console().width
                ).print(*objects, **kwargs)
                write(buffer.getvalue())
            else:
                get_console().print(*objects, **kwargs)

    def status(self, message: str) -> ContextManager[Any]:
        if state.json or state.quiet or not sys.stdout.isatty() or os.environ.get("CI"):
            return nullcontext()
        return get_console().status(message)


console = UIConsole()


def output(data: Any, message: str | None = None) -> None:
    state.data = data
    if state.json or state.quiet:
        return
    if message:
        console.print(message, markup=False)
    elif isinstance(data, list):
        table = Table(title="Tasks", header_style="highlight", expand=False)
        for name in ("ID", "Title", "Priority", "Due", "Status"):
            table.add_column(name)
        for item in data:
            table.add_row(
                str(item.get("id", "")),
                str(item.get("title", "")),
                str(item.get("priority", "medium")),
                relative_date(item.get("due_date")),
                "done" if item.get("is_completed") else "open",
            )
        console.print(table)
        console.print(f"{len(data)} task(s)", style="dim")
    elif isinstance(data, dict):
        text = "\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in data.items())
        console.print(Panel(text, title="Flunky", border_style="cyan"), markup=False)


def error(message: str) -> None:
    state.failed = True
    state.data = {"error": {"message": message, "help": DOCS}}
    if not state.json:
        get_console(error=True).print(
            Panel(f"{message}\n\nHelp: {DOCS}", title="Error", border_style="red"), markup=False
        )


def finish() -> None:
    if state.json:
        import orjson

        data = (
            state.data
            if state.data is not None
            else {"ok": not state.failed, "messages": state.messages}
        )
        sys.stdout.write(orjson.dumps(data, default=str).decode() + "\n")


def relative_date(value: str | None) -> str:
    if not value:
        return "—" if unicode_supported() else "-"
    from datetime import date

    days = (date.fromisoformat(value[:10]) - date.today()).days
    if days == 0:
        return "today"
    return f"in {days}d" if days > 0 else f"overdue {-days}d"


def unicode_supported() -> bool:
    return "utf" in (sys.stdout.encoding or "").lower() and os.environ.get("TERM") != "dumb"
