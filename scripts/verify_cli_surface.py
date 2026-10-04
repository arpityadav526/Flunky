"""Exercise the installed CLI, not CliRunner, against an isolated live API."""

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from typer.main import get_command

from cli.main import app

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", type=Path, required=True)
    args = parser.parse_args()
    executable = str(args.cli.resolve())
    count = 0
    with tempfile.TemporaryDirectory(prefix="flunky-surface-") as directory:
        work = Path(directory)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite+aiosqlite:///{work}/server.db",
            "FLUNKY_API_URL": base,
            "FLUNKY_CONFIG_DIR": str(work / "config"),
            "FLUNKY_DATA_DIR": str(work / "data"),
            "FLUNKY_PROJECTS_DIR": str(work),
            "FLUNKY_TOKEN_STORAGE": "file",
            "FLUNKY_MAILBOX_DIR": str(work / "mailbox"),
            "BROWSER": "true",
            "NO_COLOR": "1",
            "CI": "1",
        }
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
        )

        def cli(*argv, code=0, input=None, structured=True):
            nonlocal count
            command = [executable, *(["--json"] if structured else []), *argv]
            result = subprocess.run(
                command, cwd=work, env=env, input=input, text=True, capture_output=True, timeout=45
            )
            assert result.returncode == code, (
                f"{argv}: {result.returncode}\n{result.stdout}\n{result.stderr}"
            )
            assert "Traceback" not in result.stdout + result.stderr, argv
            value = json.loads(result.stdout) if structured else result.stdout
            count += 1
            print("PASS", " ".join(("flunky", *argv)), flush=True)
            return value

        def help_tree(command, path=()):
            cli(*path, "--help", structured=False)
            for name, child in getattr(command, "commands", {}).items():
                help_tree(child, (*path, name))

        help_tree(get_command(app))
        cli("--version", structured=False)
        cli()
        cli("ai")
        cli("tui", code=1)
        cli("add", "unauthenticated", code=1)
        for profile in ("staging", "prod", "local"):
            cli("config", "profile", profile)
            cli("config", "set", "api_url", base)
        cli("config", "set", "theme", "high-contrast")
        cli("config", "get", "theme")
        cli("config", "list")
        cli("config", "get", "missing", code=1)
        for shell in ("zsh", "bash", "fish", "powershell", "pwsh"):
            cli("completion", "install", shell, "--path", str(work / f"completion.{shell}"))
        for stack in (
            "python",
            "cli",
            "fastapi",
            "ds",
            "nextjs",
            "mern",
            "nestjs",
            "electron",
            "react-native",
            "flutter",
        ):
            cli("init", f"project-{stack}", "--stack", stack, "--yes")
            subprocess.run(
                [sys.executable, "scripts/check.py"],
                cwd=work / f"project-{stack}",
                check=True,
                capture_output=True,
            )
        cli(
            "init",
            "fullstack",
            "--stack",
            "fastapi",
            "--type",
            "fullstack",
            "--addons",
            "docker,ci",
            "--dry-run",
        )
        assert not (work / "fullstack").exists()
        cli("init", "create", "python", "legacy")
        cli("structure", "apply", "legacy", "--dry-run")
        cli("structure", "apply", "legacy", "--yes")
        cli("projects", "add", "demo", str(work / "legacy"))
        assert "demo" in cli("projects", "list")
        cli("projects", "remove", "demo")
        cli("projects", "remove", "demo", code=1)
        log = (work / "server.log").open("w")

        def start():
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port)],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            for _ in range(100):
                try:
                    if httpx.get(base + "/ready", timeout=1).status_code == 200:
                        return process
                except httpx.RequestError:
                    pass
                time.sleep(0.1)
            process.terminate()
            raise RuntimeError("Server failed to become ready")

        server = start()
        try:
            cli(
                "register",
                "--username",
                "surface",
                "--email",
                "surface@example.com",
                "--password-stdin",
                input="strong-password\n",
            )
            cli(
                "login",
                "--with-password",
                "--username",
                "surface",
                "--password-stdin",
                input="strong-password\n",
            )
            cli("doctor")
            cli("task", "create", "-t", "Legacy task", "-d", "description")
            cli("task", "update", "1", "--title", "Updated legacy")
            cli("task", "complete", "1")
            assert cli("task", "show", "1")["is_completed"] is True
            cli("task", "list", "--completed")
            cli("task", "delete", "1", "--force")
            cli("task", "delete", "1", "--force", code=1)
            task = cli("add", "Quick task", "-p", "high", "-d", "tomorrow", "-t", "backend")
            task_id = str(task["id"])
            cli(
                "list",
                "--priority",
                "high",
                "--tag",
                "backend",
                "--search",
                "Quick",
                "--sort=-priority",
            )
            cli("today")
            cli("upcoming")
            cli("edit", task_id, "--title", "Edited quick task", "--notes", "verified")
            cli("done", task_id)
            assert cli("show", task_id)["is_completed"] is True
            cli("undo")
            assert cli("show", task_id)["is_completed"] is False
            cli("rm", task_id, "--yes")
            cli("undo")
            cli("show", task_id)
            cli("sync")
            cli()
            server.terminate()
            server.wait(timeout=10)
            local = cli("add", "Offline task")
            assert local["offline"] and local["id"] < 0
            local_id = str(local["id"])
            cli("done", "--", local_id)
            # --json belongs before the literal separator for negative IDs.
            assert cli("list")["offline"] is True
            server = start()
            assert cli("sync")["synced"] == 2
            synced = cli("list", "--search", "Offline task")["tasks"]
            assert len(synced) == 1 and synced[0]["is_completed"]
            cli("logout", "--everywhere")
            cli("show", task_id, code=1)
            # Device approval through the real HTTP form, without opening a user browser.
            process = subprocess.Popen(
                [executable, "login", "--json"],
                cwd=work,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                user_code = None
                for _ in range(100):
                    with sqlite3.connect(work / "server.db") as db:
                        row = db.execute(
                            "SELECT user_code FROM device_flows ORDER BY rowid DESC LIMIT 1"
                        ).fetchone()
                    if row:
                        user_code = row[0]
                        break
                    time.sleep(0.1)
                assert user_code
                response = httpx.post(
                    base + "/v1/auth/device/verify",
                    data={"code": user_code, "username": "surface", "password": "strong-password"},
                )
                assert response.status_code == 200, response.text
                out, err = process.communicate(timeout=20)
                assert process.returncode == 0, out + err
                json.loads(out)
                count += 1
                print("PASS flunky login (device approval)", flush=True)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
            cli("logout")
        finally:
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=10)
            log.close()
        print(
            f"PASS {count} real installed CLI invocations; all registered command paths exercised"
        )


if __name__ == "__main__":
    main()
