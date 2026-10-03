"""Isolated live API + real CLI smoke test; never touches a user's DB/keychain."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="flunky-smoke-") as directory:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite+aiosqlite:///{directory}/smoke.db",
            "FLUNKY_API_URL": base,
            "FLUNKY_CONFIG_DIR": directory,
            "FLUNKY_TOKEN_STORAGE": "file",
            "FLUNKY_MAILBOX_DIR": str(Path(directory) / "mailbox"),
        }
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True
        )
        with (Path(directory) / "server.log").open("w") as log:
            server = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port)],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                with httpx.Client(base_url=base) as client:
                    for _ in range(100):
                        try:
                            if client.get("/ready").status_code == 200:
                                break
                        except httpx.RequestError:
                            pass
                        time.sleep(0.1)
                    assert client.get("/ready").status_code == 200
                    assert (
                        client.post(
                            "/v1/register",
                            json={
                                "username": "smoke",
                                "email": "smoke@example.com",
                                "password": "strong-password",
                            },
                        ).status_code
                        == 201
                    )

                    def cli(*args: str, input: str | None = None, code: int = 0) -> str:
                        result = subprocess.run(
                            [sys.executable, "-m", "cli.main", *args],
                            cwd=ROOT,
                            env=env,
                            input=input,
                            capture_output=True,
                            text=True,
                        )
                        assert result.returncode == code, result.stdout + result.stderr
                        print("PASS flunky", *args)
                        return result.stdout

                    cli(
                        "login",
                        "--with-password",
                        "--username",
                        "smoke",
                        "--password-stdin",
                        input="strong-password\n",
                    )
                    credentials = json.loads((Path(directory) / "config.json").read_text())
                    for args in [
                        ("task", "create", "-t", "Live smoke", "-d", "Verified"),
                        ("task", "list"),
                        ("task", "complete", "1"),
                        ("task", "show", "1"),
                        ("task", "delete", "1", "--force"),
                    ]:
                        cli(*args)
                    cli("task", "delete", "1", "--force", code=1)
                    cli("logout", "--everywhere")
                    assert (
                        client.get(
                            "/v1/tasks",
                            headers={"Authorization": "Bearer " + credentials["access_token"]},
                        ).status_code
                        == 401
                    )
                    assert (
                        client.post(
                            "/v1/auth/refresh", json={"refresh_token": credentials["refresh_token"]}
                        ).status_code
                        == 401
                    )
                    print("PASS server-side access and refresh revocation")
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == "__main__":
    main()
