from datetime import timedelta
from unittest.mock import Mock

import jwt
import pytest
from fastapi import HTTPException
from typer.testing import CliRunner

from backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    passwords,
    utcnow,
    verify_password,
)
from cli import api_client, config, main


def login(client):
    client.post(
        "/v1/register",
        json={"username": "alice", "email": "alice@example.com", "password": "strong-password"},
    )
    response = client.post("/v1/login", data={"username": "alice", "password": "strong-password"})
    assert response.status_code == 200, response.text
    return response.json()


def headers(token):
    return {"Authorization": "Bearer " + token["access_token"]}


def test_argon2_and_legacy_bcrypt():
    from pwdlib.hashers.bcrypt import BcryptHasher

    raw = "legacy-password"
    assert hash_password(raw).startswith("$argon2id$")
    assert verify_password(raw, hash_password(raw))
    assert not verify_password("wrong", hash_password(raw))
    old = BcryptHasher().hash(raw)
    valid, replacement = passwords.verify_and_update(raw, old)
    assert valid and replacement.startswith("$argon2id$")


def test_refresh_rotation_reuse_revokes_entire_family(client):
    original = login(client)
    rotated = client.post("/v1/auth/refresh", json={"refresh_token": original["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    rotated = rotated.json()
    assert rotated["refresh_token"] != original["refresh_token"]
    assert client.get("/v1/auth/me", headers=headers(rotated)).status_code == 200
    assert (
        client.post(
            "/v1/auth/refresh", json={"refresh_token": original["refresh_token"]}
        ).status_code
        == 401
    )
    assert client.get("/v1/auth/me", headers=headers(rotated)).status_code == 401
    assert client.get("/v1/auth/me", headers=headers(original)).status_code == 401
    assert (
        client.post(
            "/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
        ).status_code
        == 401
    )
    assert client.post("/v1/auth/refresh", json={"refresh_token": "z" * 64}).status_code == 401


def test_logout_single_and_everywhere(client):
    first = login(client)
    second = client.post(
        "/v1/login", data={"username": "alice", "password": "strong-password"}
    ).json()
    assert client.post("/v1/auth/logout", headers=headers(first)).status_code == 204
    assert client.get("/v1/tasks", headers=headers(first)).status_code == 401
    assert client.get("/v1/tasks", headers=headers(second)).status_code == 200
    third = client.post(
        "/v1/login", data={"username": "alice", "password": "strong-password"}
    ).json()
    assert (
        client.post("/v1/auth/logout?everywhere=true", headers=headers(second)).status_code == 204
    )
    assert client.get("/v1/tasks", headers=headers(third)).status_code == 401


def test_verification_reset_change_delete_and_pat(client, isolate_auth_services):
    token = login(client)
    mail = isolate_auth_services
    verify = mail.send.call_args.args[2]
    assert (
        client.post("/v1/auth/tokens", headers=headers(token), json={"name": "ci"}).status_code
        == 403
    )
    assert (
        client.post("/v1/auth/verify-email", json={"token": verify}).json()["status"] == "verified"
    )
    assert client.post("/v1/auth/verify-email", json={"token": verify}).status_code == 400
    assert client.post("/v1/auth/verify-email", json={"token": "invalid" * 8}).status_code == 400
    pat = client.post("/v1/auth/tokens", headers=headers(token), json={"name": "ci"}).json()
    assert pat["token"].startswith("flunky_pat_")
    assert (
        client.get("/v1/tasks", headers={"Authorization": "Bearer " + pat["token"]}).status_code
        == 200
    )
    response = client.get("/v1/auth/tokens", headers=headers(token))
    assert response.json()[0]["name"] == "ci" and "token" not in response.json()[0]
    assert client.delete("/v1/auth/tokens/missing", headers=headers(token)).status_code == 404
    assert client.delete("/v1/auth/tokens/" + pat["id"], headers=headers(token)).status_code == 204
    assert (
        client.get("/v1/tasks", headers={"Authorization": "Bearer " + pat["token"]}).status_code
        == 401
    )
    assert client.post("/v1/auth/resend-verification", headers=headers(token)).status_code == 202
    assert (
        client.post("/v1/auth/password-reset", json={"email": "absent@example.com"}).status_code
        == 202
    )
    assert (
        client.post("/v1/auth/password-reset", json={"email": "alice@example.com"}).status_code
        == 202
    )
    reset = mail.send.call_args.args[2]
    assert (
        client.post(
            "/v1/auth/password-reset/confirm", json={"token": reset, "password": "new-password"}
        ).status_code
        == 200
    )
    assert client.get("/v1/tasks", headers=headers(token)).status_code == 401
    assert (
        client.post(
            "/v1/auth/password-reset/confirm", json={"token": reset, "password": "new-password"}
        ).status_code
        == 400
    )
    token = client.post("/v1/login", data={"username": "alice", "password": "new-password"}).json()
    assert (
        client.post(
            "/v1/auth/change-password",
            headers=headers(token),
            json={"current_password": "wrong", "new_password": "another-password"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/v1/auth/change-password",
            headers=headers(token),
            json={"current_password": "new-password", "new_password": "another-password"},
        ).status_code
        == 200
    )
    assert client.get("/v1/tasks", headers=headers(token)).status_code == 401
    token = client.post(
        "/v1/login", data={"username": "alice", "password": "another-password"}
    ).json()
    assert (
        client.request(
            "DELETE", "/v1/auth/account", headers=headers(token), json={"password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.request(
            "DELETE",
            "/v1/auth/account",
            headers=headers(token),
            json={"password": "another-password"},
        ).status_code
        == 204
    )
    assert client.get("/v1/tasks", headers=headers(token)).status_code == 401


def test_device_flow_and_one_time_consumption(client, monkeypatch):
    login(client)
    flow = client.post("/v1/auth/device").json()
    assert flow["user_code"]
    page = client.get("/v1/auth/device/verify")
    assert (
        page.status_code == 200
        and "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    )
    payload = {"device_code": flow["device_code"]}
    assert (
        client.post("/v1/auth/device/token", json=payload).json()["detail"]
        == "authorization_pending"
    )
    assert client.post("/v1/auth/device/token", json=payload).status_code == 429
    assert (
        client.post(
            "/v1/auth/device/verify",
            data={"code": "bad", "username": "alice", "password": "strong-password"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/v1/auth/device/verify",
            data={"code": flow["user_code"], "username": "alice", "password": "strong-password"},
        ).status_code
        == 200
    )
    from backend.routers import auth

    now = utcnow()
    monkeypatch.setattr(auth, "utcnow", lambda: now + timedelta(seconds=6))
    response = client.post("/v1/auth/device/token", json=payload)
    assert response.status_code == 200, response.text
    assert client.get("/v1/tasks", headers=headers(response.json())).status_code == 200
    assert client.post("/v1/auth/device/token", json=payload).status_code == 400
    assert (
        client.post("/v1/auth/device/token", json={"device_code": "nope" * 20}).status_code == 400
    )


def test_rate_limiting_brute_force_and_reset(client):
    login(client)
    for _ in range(5):
        assert (
            client.post("/v1/login", data={"username": "alice", "password": "wrong"}).status_code
            == 401
        )
    assert (
        client.post("/v1/login", data={"username": "alice", "password": "wrong"}).status_code == 429
    )
    for _ in range(5):
        assert (
            client.post("/v1/auth/password-reset", json={"email": "absent@example.com"}).status_code
            == 202
        )
    assert (
        client.post("/v1/auth/password-reset", json={"email": "absent@example.com"}).status_code
        == 429
    )


def test_expired_and_wrong_purpose_access():
    from backend.core.config import settings

    token = create_access_token({"sub": "alice", "sid": "session"})
    assert decode_access_token(token)["sub"] == "alice"
    from backend.Auth import verify_token

    assert verify_token(token) == "alice"
    claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"], audience="flunky-cli")
    for patch in [{"exp": 1}, {"typ": "refresh"}, {"aud": "another"}, {"iss": "another"}]:
        bad = jwt.encode({**claims, **patch}, settings.secret_key, algorithm="HS256")
        with pytest.raises(HTTPException):
            decode_access_token(bad)


def test_keyring_and_fallback(tmp_path, monkeypatch):
    import keyring

    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.delenv("FLUNKY_TOKEN_STORAGE")
    saved = {}
    monkeypatch.setattr(keyring, "get_keyring", lambda: Mock(priority=1))
    monkeypatch.setattr(
        keyring, "set_password", lambda service, name, value: saved.update(value=value)
    )
    monkeypatch.setattr(keyring, "get_password", lambda *a: saved.get("value"))
    monkeypatch.setattr(keyring, "delete_password", lambda *a: saved.clear())
    config.save_token("access", "refresh")
    assert not config.CONFIG_FILE.exists()
    assert config.load_credentials()["refresh_token"] == "refresh"
    config.delete_token()
    assert config.load_token() is None
    monkeypatch.setattr(keyring, "set_password", Mock(side_effect=keyring.errors.KeyringError()))
    config.save_token("fallback")
    assert config.load_token() == "fallback"
    import os

    if os.name != "nt":
        assert config.CONFIG_FILE.stat().st_mode & 0o777 == 0o600
    monkeypatch.setenv("FLUNKY_API_URL", "https://different.example")
    assert config.load_token() is None
    monkeypatch.setattr(keyring, "delete_password", Mock(side_effect=keyring.errors.KeyringError()))
    config.delete_token()
    assert config.load_token() is None


def test_cli_device_login_and_server_logout(tmp_path, monkeypatch, respx_mock):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr("webbrowser.open", Mock())
    monkeypatch.setattr("time.sleep", Mock())
    base = api_client.BASE_URL
    respx_mock.post(base + "/v1/auth/device").respond(
        200,
        json={
            "device_code": "x" * 30,
            "user_code": "ABCD1234",
            "verification_uri": base + "/v1/auth/device/verify",
            "expires_in": 600,
            "interval": 5,
        },
    )
    route = respx_mock.post(base + "/v1/auth/device/token")
    import httpx

    route.side_effect = [
        httpx.Response(400, json={"detail": "authorization_pending"}),
        httpx.Response(200, json={"access_token": "access", "refresh_token": "refresh"}),
    ]
    runner = CliRunner()
    result = runner.invoke(main.app, ["login"])
    assert result.exit_code == 0, result.output
    assert config.load_token() == "access"
    logout = respx_mock.post(base + "/v1/auth/logout").respond(503)
    assert runner.invoke(main.app, ["logout"]).exit_code == 1
    assert config.load_token() == "access"
    logout.respond(204)
    assert runner.invoke(main.app, ["logout", "--everywhere"]).exit_code == 0
    assert config.load_token() is None


def test_refresh_expiry_and_automatic_cli_refresh(client, monkeypatch, tmp_path, respx_mock):
    token = login(client)
    from backend.services import auth

    future = utcnow() + timedelta(days=31)
    monkeypatch.setattr(auth, "utcnow", lambda: future)
    assert (
        client.post("/v1/auth/refresh", json={"refresh_token": token["refresh_token"]}).status_code
        == 401
    )
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    expired = jwt.encode({"sub": "alice", "exp": 1}, "x" * 32, algorithm="HS256")
    config.save_token(expired, "refresh-secret")
    respx_mock.post(api_client.BASE_URL + "/v1/auth/refresh").respond(
        200, json={"access_token": "replacement", "refresh_token": "rotated"}
    )
    assert config.load_token() == "replacement"
    assert config.load_credentials()["refresh_token"] == "rotated"


def test_dev_mailbox_does_not_log_token(tmp_path, monkeypatch, caplog):
    from backend.core.mail import ConsoleMailer

    monkeypatch.setenv("FLUNKY_MAILBOX_DIR", str(tmp_path))
    ConsoleMailer().send("test@example.com", "verify_email", "secret-token-value")
    import json

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["token"] == "secret-token-value"
    assert "secret-token-value" not in caplog.text


def test_resend_unverified(client, isolate_auth_services):
    token = login(client)
    assert client.post("/v1/auth/resend-verification", headers=headers(token)).status_code == 202
    assert isolate_auth_services.send.call_count == 2
