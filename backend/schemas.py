from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Boolean


class UserCreate(BaseModel):
    username:str
    password:str
    email:str

class UserResponse(BaseModel):
    username:str
    is_active:Boolean
    created_at:datetime
    user_id:int
    email:str

class TaskCreate(BaseModel):
    task_description:str |None=None
    task_title:str

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    is_completed: bool | None = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    is_completed: bool
    created_at: datetime
    user_id: int

class Token(BaseModel):
    access_token: str      # The actual JWT string
    token_type: str        # Usually "bearer"