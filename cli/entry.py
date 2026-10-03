"""Fast launcher: root help/version do not load HTTP, prompts, or the backend."""

import sys
from pathlib import Path


def main() -> None:
    args = sys.argv[1:]
    if args in (["--help"], ["-h"]):
        from cli.fast_output import write

        write(Path(__file__).with_name("help.txt").read_text(encoding="utf-8"))
        return
    if args == ["--version"]:
        from cli.fast_output import write

        write("flunky 0.1.0\n")
        return
    from cli.main import app

    app()
