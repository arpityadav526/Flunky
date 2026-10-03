"""Isolated Postgres 16 and final Docker API smoke; deletes only its own containers/network."""

import secrets
import subprocess
import time

import httpx


def docker(*args):
    result = subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True, timeout=180
    )
    return result.stdout.strip()


def main():
    suffix = secrets.token_hex(4)
    network, database, api = (f"flunky-verify-{suffix}-{part}" for part in ("net", "db", "api"))
    password = secrets.token_urlsafe(24)
    url = f"postgresql+asyncpg://flunky:{password}@{database}:5432/flunky"
    environment = [
        "-e",
        f"DATABASE_URL={url}",
        "-e",
        "ENVIRONMENT=production",
        "-e",
        f"SECRET_KEY={secrets.token_urlsafe(48)}",
    ]
    docker("network", "create", network)
    try:
        docker(
            "run",
            "-d",
            "--name",
            database,
            "--network",
            network,
            "-e",
            "POSTGRES_USER=flunky",
            "-e",
            f"POSTGRES_PASSWORD={password}",
            "-e",
            "POSTGRES_DB=flunky",
            "postgres:16-alpine",
        )
        for _ in range(60):
            result = subprocess.run(
                ["docker", "exec", database, "pg_isready", "-U", "flunky"], capture_output=True
            )
            if result.returncode == 0:
                break
            time.sleep(0.5)
        docker(
            "run",
            "--rm",
            "--network",
            network,
            *environment,
            "flunky:final",
            "alembic",
            "upgrade",
            "head",
        )
        docker(
            "run",
            "-d",
            "--name",
            api,
            "--network",
            network,
            "-p",
            "127.0.0.1::8000",
            *environment,
            "flunky:final",
        )
        port = docker("port", api, "8000/tcp").rsplit(":", 1)[1]
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
            for _ in range(100):
                try:
                    if client.get("/ready").status_code == 200:
                        break
                except httpx.RequestError:
                    pass
                time.sleep(0.2)
            assert client.get("/ready").status_code == 200
            assert (
                client.post(
                    "/v1/register",
                    json={
                        "username": "docker-smoke",
                        "email": "docker@example.com",
                        "password": "strong-password",
                    },
                ).status_code
                == 201
            )
            token = client.post(
                "/v1/login", data={"username": "docker-smoke", "password": "strong-password"}
            ).json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"
            response = client.post(
                "/v1/tasks",
                json={"task_title": "Postgres smoke", "priority": "high", "tags": ["verified"]},
            )
            assert response.status_code == 201, response.text
            task_id = response.json()["id"]
            rows = client.get("/v1/tasks", params={"tag": "verified", "priority": "high"}).json()
            assert len(rows) == 1
            assert client.delete(f"/v1/tasks/{task_id}").status_code in (200, 204)
            assert client.post(f"/v1/tasks/{task_id}/restore").status_code == 200
            assert client.post("/v1/auth/logout", json={"everywhere": True}).status_code in (
                200,
                204,
            )
            assert client.get("/v1/tasks").status_code == 401
        print(
            "PASS Postgres 16 migrations, two-worker API readiness, auth, task creation/filtering/delete/restore, logout revocation"
        )
        print("Image bytes:", docker("image", "inspect", "flunky:final", "--format", "{{.Size}}"))
        print(
            "Runtime user:",
            docker("image", "inspect", "flunky:final", "--format", "{{.Config.User}}"),
        )
    finally:
        for container in (api, database):
            subprocess.run(["docker", "rm", "-fv", container], capture_output=True)
        subprocess.run(["docker", "network", "rm", network], capture_output=True)


if __name__ == "__main__":
    main()
