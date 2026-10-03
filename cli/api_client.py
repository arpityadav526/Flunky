"""HTTP boundary. Never report a mutation as successful without a successful response."""

import os
from typing import Any, cast

import httpx

BASE_URL = os.environ.get("FLUNKY_API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = httpx.Timeout(10.0, connect=3.0)


class APIError(Exception):
    """A safe, actionable error returned to a CLI command."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def get_auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token.strip()}"}


def _request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    form: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    try:
        with httpx.Client(timeout=TIMEOUT, transport=httpx.HTTPTransport(retries=2)) as client:
            from cli.settings import api_url

            url = api_url()
            response = client.request(
                method,
                f"{url}{path}",
                headers=get_auth_headers(token) if token else {},
                json=payload,
                data=form,
                params=params,
            )
    except httpx.RequestError:
        raise APIError(
            f"Can't reach {BASE_URL}. Is the server running? Try `flunky doctor`."
        ) from None
    if response.status_code not in (200, 201, 204):
        fallback = {
            401: "Not authenticated. Run `flunky login`.",
            403: "Not authorized to access this task.",
            404: "Task not found. Run `flunky task list` to see available tasks.",
        }
        detail = fallback.get(response.status_code, f"Server returned HTTP {response.status_code}.")
        if response.status_code not in fallback:
            try:
                body = response.json()
                if isinstance(body, dict):
                    detail = str(body.get("detail", detail))
            except ValueError:
                pass
        raise APIError(detail, response.status_code)
    if response.status_code == 204 or not response.content:
        return None
    try:
        body = response.json()
        from pydantic import TypeAdapter

        from cli.models import Device, Task, Token, User

        model: Any = None
        if path.endswith("/login") or path.endswith("/refresh") or path.endswith("/device/token"):
            model = Token
        elif path.endswith("/register") or path.endswith("/auth/me"):
            model = User
        elif path.endswith("/auth/device"):
            model = Device
        elif "/tasks" in path and "/bulk/" not in path:
            model = list[Task] if isinstance(body, list) else Task
        return (
            TypeAdapter(model).validate_python(body).model_dump(mode="json", exclude_unset=True)
            if model and not isinstance(body, list)
            else (
                [
                    item.model_dump(mode="json", exclude_unset=True)
                    for item in TypeAdapter(model).validate_python(body)
                ]
                if model
                else body
            )
        )
    except ValueError:
        raise APIError("Server returned invalid JSON. Check the server version.") from None


def register_user(username: str, email: str, password: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request(
            "POST",
            "/register",
            payload={
                "username": username,
                "email": email,
                "password": password,
            },
        ),
    )


def login_user(username: str, password: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request(
            "POST",
            "/login",
            form={
                "username": username,
                "password": password,
            },
        ),
    )


def task_func(title: str, description: str, token: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _request(
            "POST",
            "/tasks",
            token=token,
            payload={
                "task_title": title,
                "task_description": description,
            },
        ),
    )


def get_all_task(token: str, completed: bool | None = None) -> list[dict[str, Any]]:
    params = {} if completed is None else {"completed": completed}
    return cast(list[dict[str, Any]], _request("GET", "/tasks", token=token, params=params))


def get_task_by_id(task_id: int, token: str) -> dict[str, Any]:
    return cast(dict[str, Any], _request("GET", f"/tasks/{task_id}", token=token))


def update_task(
    task_id: int,
    token: str,
    title: str | None = None,
    description: str | None = None,
    is_completed: bool | None = None,
) -> dict[str, Any]:
    values = {"title": title, "description": description, "is_completed": is_completed}
    payload = {key: value for key, value in values.items() if value is not None}
    return cast(dict[str, Any], _request("PUT", f"/tasks/{task_id}", token=token, payload=payload))


def delete_task(task_id: int, token: str) -> None:
    _request("DELETE", f"/tasks/{task_id}", token=token)
