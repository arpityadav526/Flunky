"""Provider contracts only; no agent or external calls are implemented."""

from typing import Protocol

import typer

from cli.ui.commands import FlunkyGroup


class Provider(Protocol):
    async def complete(self, prompt: str) -> str: ...


app = typer.Typer(
    cls=FlunkyGroup,
    help="Reserved provider extension; no AI agent is implemented.",
    invoke_without_command=True,
)


@app.callback()
def reserved() -> None:
    """Reserved for a future provider integration."""
    from cli import ui

    ui.output({"available": False}, "AI integration is not implemented.")
