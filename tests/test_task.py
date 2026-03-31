def create_user_and_get_token(client):
    client.post(
        "/register",
        json={
            "username": "arpit",
            "email": "arpit@test.com",
            "password": "testpass123"
        }
    )

    login_response = client.post(
        "/login",
        data={
            "username": "arpit",
            "password": "testpass123"
        }
    )

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_task_success(client):
    headers = create_user_and_get_token(client)

    response = client.post(
        "/tasks",
        json={
            "task_title": "Learn FastAPI",
            "task_description": "Finish project testing"
        },
        headers=headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Learn FastAPI"
    assert data["description"] == "Finish project testing"
    assert data["is_completed"] is False


def test_create_task_unauthorized(client):
    response = client.post(
        "/tasks",
        json={
            "task_title": "Unauthorized task",
            "task_description": "Should fail"
        }
    )

    assert response.status_code == 401


def test_list_tasks(client):
    headers = create_user_and_get_token(client)

    client.post(
        "/tasks",
        json={
            "task_title": "Task 1",
            "task_description": "Desc 1"
        },
        headers=headers
    )

    client.post(
        "/tasks",
        json={
            "task_title": "Task 2",
            "task_description": "Desc 2"
        },
        headers=headers
    )

    response = client.get("/tasks", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_single_task(client):
    headers = create_user_and_get_token(client)

    create_response = client.post(
        "/tasks",
        json={
            "task_title": "Single task",
            "task_description": "Read one task"
        },
        headers=headers
    )

    task_id = create_response.json()["id"]

    response = client.get(f"/tasks/{task_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == "Single task"


def test_update_task(client):
    headers = create_user_and_get_token(client)

    create_response = client.post(
        "/tasks",
        json={
            "task_title": "Old title",
            "task_description": "Old desc"
        },
        headers=headers
    )

    task_id = create_response.json()["id"]

    response = client.put(
        f"/tasks/{task_id}",
        json={
            "title": "New title",
            "description": "New desc",
            "is_completed": True
        },
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New title"
    assert data["description"] == "New desc"
    assert data["is_completed"] is True


def test_delete_task(client):
    headers = create_user_and_get_token(client)

    create_response = client.post(
        "/tasks",
        json={
            "task_title": "Delete me",
            "task_description": "To be removed"
        },
        headers=headers
    )

    task_id = create_response.json()["id"]

    delete_response = client.delete(f"/tasks/{task_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_response.status_code == 404