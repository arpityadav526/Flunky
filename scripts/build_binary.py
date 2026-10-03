"""Build a CLI executable on the target platform; no cross-compilation."""

import subprocess
import sys

subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--specpath",
        "build",
        "--onefile",
        "--name",
        "flunky",
        "--paths",
        ".",
        "--collect-all",
        "cli",
        "--collect-all",
        "textual",
        "--collect-all",
        "dateparser",
        "--collect-all",
        "keyring",
        "--copy-metadata",
        "flunky",
        "packaging/launcher.py",
    ],
    check=True,
)
