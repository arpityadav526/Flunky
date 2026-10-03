"""Refresh the lightweight launcher's root help from the real Typer application."""

import os
from pathlib import Path

os.environ["NO_COLOR"] = "1"
from typer.testing import CliRunner

from cli.main import app

result = CliRunner().invoke(app, ["--help"], color=False, prog_name="flunky")
if result.exit_code:
    raise RuntimeError(result.output)
Path("cli/help.txt").write_text(result.stdout, encoding="utf-8")
