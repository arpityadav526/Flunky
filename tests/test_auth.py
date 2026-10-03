def test_register_user_success(client):
    response = client.post(
        "/register",
        json={"username": "arpit", "email": "arpit@test.com", "password": "testpass123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "arpit"
    assert data["email"] == "arpit@test.com"
    assert "id" in data


def test_register_duplicate_username(client):
    client.post(
        "/register", json={"username": "arpit", "email": "a1@test.com", "password": "testpass123"}
    )

    response = client.post(
        "/register", json={"username": "arpit", "email": "a2@test.com", "password": "testpass123"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Username already taken"


def test_register_duplicate_email(client):
    client.post(
        "/register",
        json={"username": "arpit1", "email": "arpit@test.com", "password": "testpass123"},
    )

    response = client.post(
        "/register",
        json={"username": "arpit2", "email": "arpit@test.com", "password": "testpass123"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_login_success(client):
    client.post(
        "/register",
        json={"username": "arpit", "email": "arpit@test.com", "password": "testpass123"},
    )

    response = client.post("/login", data={"username": "arpit", "password": "testpass123"})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_username(client):
    response = client.post("/login", data={"username": "wronguser", "password": "testpass123"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_invalid_password(client):
    client.post(
        "/register",
        json={"username": "arpit", "email": "arpit@test.com", "password": "testpass123"},
    )

    response = client.post("/login", data={"username": "arpit", "password": "wrongpass"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_invalid_expired_and_missing_subject(client):
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from backend.config import ALGORITHM, SECRET_KEY

    for token in [
        "broken",
        jwt.encode(
            {"exp": datetime.now(timezone.utc) - timedelta(seconds=1), "sub": "arpit"},
            SECRET_KEY,
            algorithm=ALGORITHM,
        ),
        jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
            SECRET_KEY,
            algorithm=ALGORITHM,
        ),
        jwt.encode({"sub": "missing"}, SECRET_KEY, algorithm=ALGORITHM),
    ]:
        assert client.get("/tasks", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_password_byte_limit(client):
    response = client.post(
        "/register", json={"username": "long", "email": "long@test.com", "password": "🦋" * 20}
    )
    assert response.status_code == 422
