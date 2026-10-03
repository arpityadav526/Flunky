from datetime import date
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Select, case, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from backend.models import Task


async def owned_task(
    db: AsyncSession, task_id: int, user_id: int, *, deleted: bool = False
) -> Task:
    task = await db.get(Task, task_id)
    if task is None or (task.deleted_at is not None and not deleted):
        raise HTTPException(404, "Task not found")
    if task.user_id != user_id:
        raise HTTPException(403, "Not authorized to access this task")
    return task


def task_query(
    user_id: int,
    completed: bool | None,
    priority: str | None,
    search: str | None,
    due_before: date | None,
    due_after: date | None,
    deleted: bool,
    sort: str,
    tag: str | None = None,
    dialect: str = "sqlite",
) -> Select[tuple[Task]]:
    query = select(Task).where(Task.user_id == user_id)
    query = query.where(Task.deleted_at.is_not(None) if deleted else Task.deleted_at.is_(None))
    if completed is not None:
        query = query.where(Task.is_completed == completed)
    if priority is not None:
        query = query.where(Task.priority == priority)
    if search:
        query = query.where(Task.title.contains(search, autoescape=True))
    if due_before:
        query = query.where(Task.due_date <= due_before)
    if due_after:
        query = query.where(Task.due_date >= due_after)
    if tag is not None:
        tags = (
            func.json_each(Task.tags)
            if dialect == "sqlite"
            else func.json_array_elements_text(Task.tags)
        ).table_valued("value")
        query = query.where(exists(select(1).select_from(tags).where(tags.c.value == tag)))
    columns = {
        "created_at": Task.created_at,
        "due_date": Task.due_date,
        "title": Task.title,
        "updated_at": Task.updated_at,
    }
    order: ColumnElement[Any] | InstrumentedAttribute[Any]
    if sort.lstrip("-") == "priority":
        order = case((Task.priority == "high", 0), (Task.priority == "medium", 1), else_=2)
    else:
        order = columns[sort.lstrip("-")]
    return query.order_by(order.desc() if sort.startswith("-") else order.asc(), Task.id)
