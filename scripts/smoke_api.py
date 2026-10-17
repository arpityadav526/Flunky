"""Exercise a deployed API with a temporary account; remove it afterwards."""

import os
import secrets

import httpx


def main() -> None:
    username = "smoke_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    with httpx.Client(base_url=os.environ.get("FLUNKY_API_URL", "http://127.0.0.1:8000")) as client:
        client.get("/ready").raise_for_status()
        response = client.post(
            "/v1/register",
            json={"username": username, "email": f"{username}@example.com", "password": password},
        )
        response.raise_for_status()
        response = client.post("/v1/login", data={"username": username, "password": password})
        response.raise_for_status()
        client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        try:
            response = client.post(
                "/v1/tasks", json={"task_title": "Container smoke", "tags": ["ci"]}
            )
            response.raise_for_status()
            task_id = response.json()["id"]
            response = client.get("/v1/tasks", params={"tag": "ci"})
            response.raise_for_status()
            assert any(task["id"] == task_id for task in response.json())
            response = client.put(f"/v1/tasks/{task_id}", json={"is_completed": True})
            response.raise_for_status()
            assert response.json()["is_completed"] is True
            client.delete(f"/v1/tasks/{task_id}").raise_for_status()
            assert client.get(f"/v1/tasks/{task_id}").status_code == 404
            print(
                "PASS readiness, registration, login, task creation/filtering/completion/deletion"
            )
        finally:
            client.request(
                "DELETE", "/v1/auth/account", json={"password": password}
            ).raise_for_status()


if __name__ == "__main__":
    main()
