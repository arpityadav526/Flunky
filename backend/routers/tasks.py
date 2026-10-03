from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.Auth import get_current_user
from backend.database import get_db
from backend.models import User
from backend.repositories.tasks import owned_task, task_query
from backend.schemas import BulkTasks, Priority, TaskCreate, TaskResponse, TaskUpdate
from backend.services import tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Sort = Literal[
    "created_at",
    "-created_at",
    "due_date",
    "-due_date",
    "priority",
    "-priority",
    "title",
    "-title",
    "updated_at",
    "-updated_at",
]


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(value: TaskCreate, db: DB, user: CurrentUser) -> TaskResponse:
    return TaskResponse.model_validate(await tasks.create(db, user.id, value))


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    db: DB,
    user: CurrentUser,
    response: Response,
    completed: bool | None = None,
    priority: Priority | None = None,
    tag: str | None = None,
    search: str | None = None,
    due_before: date | None = None,
    due_after: date | None = None,
    deleted: bool = False,
    sort: Sort = "created_at",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskResponse]:
    query = task_query(
        user.id,
        completed,
        priority,
        search,
        due_before,
        due_after,
        deleted,
        sort,
        tag,
        db.get_bind().dialect.name,
    )
    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = (await db.scalars(query.offset(offset).limit(limit))).all()
    response.headers["X-Total-Count"] = str(total)
    return [TaskResponse.model_validate(row) for row in rows]


@router.post("/bulk/complete")
async def bulk_complete(value: BulkTasks, db: DB, user: CurrentUser) -> dict[str, int]:
    return {"count": await tasks.bulk(db, user.id, value.ids, delete=False)}


@router.post("/bulk/delete")
async def bulk_delete(value: BulkTasks, db: DB, user: CurrentUser) -> dict[str, int]:
    return {"count": await tasks.bulk(db, user.id, value.ids, delete=True)}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: DB, user: CurrentUser) -> TaskResponse:
    return TaskResponse.model_validate(await owned_task(db, task_id, user.id))


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, value: TaskUpdate, db: DB, user: CurrentUser) -> TaskResponse:
    task = await owned_task(db, task_id, user.id)
    return TaskResponse.model_validate(await tasks.update(db, task, value))


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: DB, user: CurrentUser) -> Response:
    task = await owned_task(db, task_id, user.id)
    task.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return Response(status_code=204)


@router.post("/{task_id}/restore", response_model=TaskResponse)
async def restore_task(task_id: int, db: DB, user: CurrentUser) -> TaskResponse:
    task = await owned_task(db, task_id, user.id, deleted=True)
    task.deleted_at = None
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task)
