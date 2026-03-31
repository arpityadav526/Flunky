from http.client import HTTPException

import httpx
from typing import Optional, Dict, Any
from rich.console import Console


console = Console()

# Base URL of the  FastAPI backend
BASE_URL = "http://localhost:8000"


def register_user(username: str, email: str, password: str):
    payload = {
        "username": username,
        "email": email,
        "password": password,
    }

    try:
        response = httpx.post(f"{BASE_URL}/register", json=payload, timeout=10.0)

        if response.status_code in (200, 201):
            return response.json()

        try:
            error_detail = response.json().get("detail")
        except Exception:
            error_detail = response.text

        raise Exception(f"registration failed: {error_detail}")

    except httpx.RequestError as e:
        raise Exception(f"could not connect to server: {e}")


def login_user(username: str, password: str):
    payload = {
        "username": username,
        "password": password,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = httpx.post(
            f"{BASE_URL}/login",
            data=payload,
            headers=headers,
            timeout=10.0,
        )

        if response.status_code == 200:
            return response.json()

        try:
            error_detail = response.json().get("detail")
        except Exception:
            error_detail = response.text

        raise Exception(f"login failed: {error_detail}")

    except httpx.RequestError as e:
        raise Exception(f"could not connect to server: {e}")


def get_auth_headers(token: str):
   
    return {"Authorization": f"Bearer {token.strip()}"}

def task_func(description: str, title: str ,token: str)->Dict[str, any]:
    data={
        "task_title": title,
        "task_description": description,
    }
    header={
        "Authorization": f"Bearer {token.strip()}"
    }
    response=httpx.post(f"{BASE_URL}/tasks", json=data, headers=header)

    if response.status_code==201:
        return response.json()
    elif response.status_code == 401:
        raise Exception("Not authenticated. Please login first.")
    else:
        error_detail = response.json().get("detail", "Failed to create task")
        raise Exception(error_detail)



def get_all_task(token: str, completed: Optional[bool] = None)-> list:
    header={
        "Authorization": f"Bearer {token.strip()}"
    }
    params={}
    if completed is not None:
        params["Completed"]=completed


    response=httpx.get(f"{BASE_URL}/tasks",headers=header, params=params)

    if response.status_code==200:
        return response.json()
    elif response.status_code==401 :
        raise Exception("Not authenticated. Please login first.")
    else:
        raise Exception("Failed to get tasks")


def get_task_by_id(task_id: int, token: str)->Dict[str, any]:
    headers={
        "Authorization": f"Bearer {token.strip()}"
    }


    response=httpx.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)

    if response.status_code==200:
        return response.json()
    elif response.status_code==404:
        raise Exception("not found")
    else:
        raise Exception("not authorized")


def get_auth_headers(token: str):
    return {"Authorization": f"Bearer {token.strip()}"}


def update_task(task_id: int, token: str, title=None, description=None, is_completed=None):
    payload = {}

    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if is_completed is not None:
        payload["is_completed"] = is_completed

    response = httpx.put(
        f"{BASE_URL}/tasks/{task_id}",
        json=payload,
        headers=get_auth_headers(token),
        timeout=10.0,
    )

    if response.status_code == 200:
        return response.json()

    try:
        detail = response.json().get("detail")
    except Exception:
        detail = response.text

    raise Exception(detail)




def delete_task(task_id: int, token : str)->None:
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response=httpx.delete(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    if response.status_code==200:
        return response.json()







