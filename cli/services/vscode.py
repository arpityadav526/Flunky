import shutil
import subprocess
from pathlib import Path


def is_vscode_command_available() -> bool:
    return shutil.which("code") is not None


def open_in_vscode(project_path: Path) -> None:
    if not is_vscode_command_available():
        raise RuntimeError(
            "VS Code command 'code' is not available. "
            "Enable it from VS Code Command Palette: "
            "'Shell Command: Install code command in PATH'."
        )

    subprocess.run(["code", str(project_path)], check=True)