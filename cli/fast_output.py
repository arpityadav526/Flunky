"""Plain terminal output for the startup-budget-sensitive launcher."""

import os
import sys


def write(text: str) -> None:
    if os.name == "nt" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if os.environ.get("TERM") == "dumb" or "utf" not in (sys.stdout.encoding or "").lower():
        text = "".join(
            (
                "|"
                if char in "│║"
                else "-"
                if char in "─═"
                else "+"
                if 0x2500 <= ord(char) <= 0x257F
                else char
            )
            for char in text
        )
        text = text.encode("ascii", errors="replace").decode("ascii")
    sys.stdout.write(text)
