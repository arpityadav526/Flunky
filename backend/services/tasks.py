from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Task
from backend.repositories.tasks import owned_task
from backend.schemas import TaskCreate, TaskUpdate


async def create(db: AsyncSession, user_id: int, value: TaskCreate) -> Task:
    fields = value.model_dump(exclude={"task_title", "task_description"})
    task = Task(
        user_id=user_id, title=value.task_title, description=value.task_description, **fields
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update(db: AsyncSession, task: Task, value: TaskUpdate) -> Task:
    for key, field in value.model_dump(exclude_unset=True).items():
        if field is None and key in {"title", "is_completed", "priority", "tags"}:
            continue
        setattr(task, key, field)
    await db.commit()
    await db.refresh(task)
    return task


async def bulk(db: AsyncSession, user_id: int, ids: list[int], *, delete: bool) -> int:
    # Resolve the entire batch before mutating, so ownership errors cannot partially apply it.
    tasks = [await owned_task(db, task_id, user_id) for task_id in set(ids)]
    for task in tasks:
        if delete:
            task.deleted_at = datetime.now(timezone.utc)
        else:
            task.is_completed = True
    await db.commit()
    return len(tasks)
