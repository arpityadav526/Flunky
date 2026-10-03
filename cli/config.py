"""Credentials live in the OS keychain, with a private atomic file fallback."""

import base64
import json
import os
import tempfile
from pathlib import Path

from platformdirs import user_config_path

CONFIG_DIR = Path(os.environ.get("FLUNKY_CONFIG_DIR", str(user_config_path("flunky"))))
CONFIG_FILE = CONFIG_DIR / "config.json"


def server_url() -> str:
    return os.environ.get("FLUNKY_API_URL", "http://localhost:8000").rstrip("/")


def _keyring_service() -> str:
    return "flunky:" + server_url()


def _private_write(data: dict[str, str | bool]) -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="credentials-", dir=CONFIG_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(data, output)
        os.replace(name, CONFIG_FILE)
    finally:
        Path(name).unlink(missing_ok=True)


def save_token(token: str, refresh_token: str | None = None) -> None:
    data: dict[str, str | bool] = {"access_token": token.strip(), "server": server_url()}
    if refresh_token:
        data["refresh_token"] = refresh_token
    import keyring

    try:
        if os.environ.get("FLUNKY_TOKEN_STORAGE") == "file" or keyring.get_keyring().priority <= 0:
            raise keyring.errors.NoKeyringError("Keyring unavailable")
        keyring.set_password(_keyring_service(), "session", json.dumps(data))
        CONFIG_FILE.unlink(missing_ok=True)
    except (keyring.errors.KeyringError, RuntimeError):
        _private_write(data)
        from rich.console import Console

        Console(stderr=True).print(
            "Warning: OS keychain unavailable or disabled; credentials stored in a private file."
        )


def load_credentials() -> dict[str, str]:
    import keyring

    raw: str | None = None
    if CONFIG_FILE.exists():
        try:
            raw = CONFIG_FILE.read_text(encoding="utf-8")
        except OSError:
            return {}
    elif os.environ.get("FLUNKY_TOKEN_STORAGE") != "file":
        try:
            raw = keyring.get_password(_keyring_service(), "session")
        except (keyring.errors.KeyringError, RuntimeError):
            return {}
    try:
        data = json.loads(raw or "{}")
        if (
            not isinstance(data, dict)
            or data.get("logged_out")
            or data.get("server") != server_url()
        ):
            return {}
        return {key: value for key, value in data.items() if isinstance(value, str)}
    except ValueError:
        return {}


def load_token() -> str | None:
    credentials = load_credentials()
    token = credentials.get("access_token")
    refresh = credentials.get("refresh_token")
    if token and refresh:
        import time

        try:
            encoded = token.split(".")[1]
            payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
            expires = float(payload.get("exp", 0))
        except (ValueError, IndexError, TypeError):
            return token
        if expires < time.time() + 30:
            from cli.api_client import _request

            result = _request("POST", "/v1/auth/refresh", payload={"refresh_token": refresh})
            access = str(result["access_token"])
            save_token(access, str(result["refresh_token"]))
            return access
    return token


def delete_token() -> None:
    import keyring

    try:
        if os.environ.get("FLUNKY_TOKEN_STORAGE") != "file":
            keyring.delete_password(_keyring_service(), "session")
    except (keyring.errors.KeyringError, RuntimeError):
        # Prevent a locked or temporarily unavailable keychain restoring a logged-out session.
        _private_write({"logged_out": True, "server": server_url()})
        return
    CONFIG_FILE.unlink(missing_ok=True)


def is_locked_in_lmao() -> bool:
    return load_token() is not None


def get_logged_in_username() -> str | None:
    token = load_token()
    if not token:
        return None
    try:
        encoded = token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        name = payload.get("sub")
        return name if isinstance(name, str) else None
    except (ValueError, IndexError, UnicodeDecodeError):
        return None
