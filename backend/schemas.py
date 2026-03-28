from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserCreate(BaseModel):
        username: str
        password: str
        email: EmailStr

        @field_validator("password")
        @classmethod
        def validate_password_length(cls, value: str) -> str:
            if len(value.encode("utf-8")) > 72:
                raise ValueError("Password must be 72 bytes or fewer for bcrypt.")
            return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class TaskCreate(BaseModel):
    task_title: str
    task_description: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    is_completed: bool | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    is_completed: bool
    created_at: datetime
    user_id: int


class Token(BaseModel):
    access_token: str
    token_type: str