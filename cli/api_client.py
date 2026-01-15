from http.client import HTTPException

import httpx
from typing import Optional, Dict, Any
from rich.console import Console


console = Console()

# Base URL of the  FastAPI backend
BASE_URL = "http://127.0.0.1:8000"


def register_func(username:str, e_mail:str, password: str)-> Dict[str, any]:
    data={
        "username":username,
        "e-mail":e_mail,
        "password":password

    }

    response=httpx.post(f"{BASE_URL}/register", json=data)
    if response.status_code==201:
        return response.json()
    else:
        error_detail=response.json().get("detail: unknown")
        raise HTTPException(f"registration failed : {error_detail}")



def login_user(username: str, password: str)->str:
    data={
        "username":username,
        "password": password
    }
    response=httpx.post(f"{BASE_URL}/login", json=data)

    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]  # Return just the token string
    else:
        error_detail = response.json().get("detail", "Login failed")
        raise Exception(error_detail)




def task_func(description: str, title: str ,token: str)->Dict[str, any]:
    data={
        "Description": description,
        "Title":title
    }
    header={
        "authorization": f" Bearer {token}"
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
        "Authorization": f"Bearer {token}"
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
        "Authorization": f"Bearer {token}"
    }


    response=httpx.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)

    if response.status_code==200:
        return response.json()
    elif response.status_code==404:
        raise Exception("not found")
    else:
        raise Exception("not authorized")



def update_task(task_id:int , token: str, title: Optional[str] = None,
    description: Optional[str] = None,
    is_completed: Optional[bool] = None
) -> Dict[str, Any]:

    headers={
        "Authorization": f"bearer {token}"
    }

    data = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if is_completed is not None:
        data["is_completed"] = is_completed

    params = {}
    if is_completed is not None:
        params["Completed"] = is_completed


        response=httpx.post(f"{BASE_URL}/tasks/{task_id}", headers=headers, json=data, params=params)

        if response.status_code==200:
            return response.json()




def delete_task(task_id: int, token : str)->None:
    headers = {
        "Authorization": f"bearer {token}"
    }
    response=httpx.delete(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    if response.status_code==200:
        return response.json()







