import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def _path() -> Path:
    from cli.config import CONFIG_DIR

    return CONFIG_DIR / "settings.json"


def load() -> dict[str, Any]:
    try:
        value = json.loads(_path().read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Settings must be an object")
        return value
    except FileNotFoundError:
        return {
            "active_profile": "local",
            "profiles": {"local": {"api_url": "http://localhost:8000"}, "staging": {}, "prod": {}},
        }
    except ValueError as exc:
        raise ValueError(f"Invalid settings file {_path()}. Fix or remove it: {exc}") from None


def save(value: dict[str, Any]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def api_url() -> str:
    value = os.environ.get("FLUNKY_API_URL")
    if not value:
        config = load()
        value = config["profiles"].get(config["active_profile"], {}).get("api_url")
    if not isinstance(value, str) or not value:
        raise ValueError("This profile has no API URL. Run `flunky config set api_url URL`.")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("API URL must be an http(s) URL without credentials, query, or fragment.")
    if parsed.scheme == "http" and parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
        "testserver",
    }:
        raise ValueError("Remote servers require HTTPS. Use https:// for this profile.")
    return value.rstrip("/")
