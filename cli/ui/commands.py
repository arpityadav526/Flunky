from typing import Any

from typer import Exit
from typer._click import Context
from typer.core import TyperGroup

from cli import ui

FLAGS = {"--json", "--quiet", "--yes", "--debug", "--no-color"}


class FlunkyGroup(TyperGroup):
    def parse_args(self, ctx: Context, args: list[str]) -> list[str]:
        if ctx.parent is None:
            flags: set[str] = set()
            filtered: list[str] = []
            literal = False
            for arg in args:
                if arg == "--":
                    literal = True
                if not literal and arg in FLAGS:
                    flags.add(arg)
                else:
                    filtered.append(arg)
            ui.configure(flags)
            args = filtered
        return super().parse_args(ctx, args)

    def invoke(self, ctx: Context) -> Any:
        if ctx.parent is not None:
            return super().invoke(ctx)
        try:
            return super().invoke(ctx)
        except Exit as exc:
            if exc.exit_code:
                if ui.state.quiet and not ui.state.json:
                    ui.error(
                        ui.state.messages[-1]
                        if ui.state.messages
                        else "Command failed. Run again without --quiet for details."
                    )
                ui.state.failed = True
                ui.state.data = {
                    "error": {
                        "message": "Command failed",
                        "details": ui.state.messages,
                        "help": ui.DOCS,
                    }
                }
            raise
        except (KeyboardInterrupt, EOFError):
            ui.error("Cancelled. No further changes were made.")
            ctx.exit(130)
        except Exception as exc:
            if ui.state.debug:
                raise
            ui.error(str(exc))
            ctx.exit(1)
        finally:
            ui.finish()

    def get_help(self, ctx: Context) -> str:
        help_text = super().get_help(ctx)
        return (
            help_text
            + "\nGlobal flags (before or after a command): --json --quiet --no-color --yes --debug\n"
        )
