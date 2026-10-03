from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Priority = Literal["low", "medium", "high"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=1024)
    email: EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    created_at: datetime


class TaskCreate(BaseModel):
    client_id: str | None = Field(default=None, max_length=36)
    task_title: str = Field(min_length=1, max_length=255)
    task_description: str | None = Field(default=None, max_length=10000)
    priority: Priority = "medium"
    due_date: date | None = None
    tags: list[str] = Field(default_factory=list, max_length=30)
    notes: str | None = Field(default=None, max_length=50000)

    @field_validator("task_title")
    @classmethod
    def nonempty_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title cannot be blank")
        return value.strip()


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    is_completed: bool | None = None
    priority: Priority | None = None
    due_date: date | None = None
    tags: list[str] | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=50000)

    @field_validator("title")
    @classmethod
    def nonempty_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Title cannot be blank")
        return value.strip() if value is not None else None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str | None = None
    is_completed: bool
    created_at: datetime
    user_id: int
    priority: Priority
    due_date: date | None
    tags: list[str]
    notes: str | None
    updated_at: datetime
    deleted_at: datetime | None


class BulkTasks(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    expires_in: int = 900


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=1024)


class EmailRequest(BaseModel):
    email: EmailStr


class ActionRequest(BaseModel):
    token: str = Field(min_length=20, max_length=1024)


class ResetRequest(ActionRequest):
    password: str = Field(min_length=8, max_length=1024)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=1024)
    new_password: str = Field(min_length=8, max_length=1024)


class AccountDelete(BaseModel):
    password: str = Field(max_length=1024)


class PATRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_days: int = Field(default=30, ge=1, le=365)


class DevicePoll(BaseModel):
    device_code: str = Field(min_length=20, max_length=1024)
