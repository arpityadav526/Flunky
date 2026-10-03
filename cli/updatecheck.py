"""A best-effort background check; only cached results are shown in the foreground."""

import json
import os
import sys
import threading
import time
from pathlib import Path

from platformdirs import user_cache_path

from cli import ui


def cache_file() -> Path:
    return Path(os.environ.get("FLUNKY_CACHE_DIR", str(user_cache_path("flunky")))) / "update.json"


def fetch() -> None:
    try:
        import httpx

        response = httpx.get("https://pypi.org/pypi/flunky/json", timeout=1.0)
        response.raise_for_status()
        latest = response.json()["info"]["version"]
        path = cache_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"checked": time.time(), "version": latest}), encoding="utf-8")
    except (OSError, ValueError, KeyError, httpx.HTTPError):
        return


def notify() -> None:
    if (
        not sys.stdout.isatty()
        or os.environ.get("CI")
        or os.environ.get("FLUNKY_NO_UPDATE_CHECK")
        or ui.state.json
        or ui.state.quiet
    ):
        return
    try:
        data = json.loads(cache_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    latest = str(data.get("version", "0.1.0"))
    from packaging.version import InvalidVersion, Version

    try:
        if Version(latest) > Version("0.1.0"):
            ui.console.print(
                f"Flunky {latest} is available. Update with `uv tool upgrade flunky`.", markup=False
            )
    except InvalidVersion:
        pass
    if time.time() - data.get("checked", 0) > 86400:
        threading.Thread(target=fetch, daemon=True).start()
