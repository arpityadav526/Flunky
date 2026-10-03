"""Plain terminal output for the startup-budget-sensitive launcher."""

import sys


def write(text: str) -> None:
    sys.stdout.write(text)
