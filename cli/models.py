from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Task(APIModel):
    id: int
    title: str
    description: str | None = None
    is_completed: bool = False
    created_at: datetime | None = None
    user_id: int | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class User(APIModel):
    id: int | None = None
    username: str
    email: str | None = None
    created_at: datetime | None = None


class Token(APIModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 900


class Device(APIModel):
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int
