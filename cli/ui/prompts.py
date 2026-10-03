import os
import sys
from typing import Any

import questionary as library

from cli import ui


class Prompt:
    def __init__(self, kind: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.kind, self.args, self.kwargs = kind, args, kwargs

    def ask(self) -> Any:
        if self.kind == "confirm" and ui.state.yes:
            return True
        if not sys.stdin.isatty() or os.environ.get("CI"):
            raise ValueError(
                "Interactive input is unavailable. Supply command flags; use --yes to confirm."
            )
        return getattr(library, self.kind)(*self.args, **self.kwargs).ask()


class Prompts:
    def text(self, *args: Any, **kwargs: Any) -> Prompt:
        return Prompt("text", args, kwargs)

    def password(self, *args: Any, **kwargs: Any) -> Prompt:
        return Prompt("password", args, kwargs)

    def confirm(self, *args: Any, **kwargs: Any) -> Prompt:
        return Prompt("confirm", args, kwargs)

    def autocomplete(self, *args: Any, **kwargs: Any) -> Prompt:
        return Prompt("autocomplete", args, kwargs)


questionary = Prompts()
