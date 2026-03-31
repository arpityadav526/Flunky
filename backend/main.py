from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from starlette.status import HTTP_201_CREATED

from backend.database import engine, get_db
from backend import models, schemas
from backend.logger import logger
from backend.Auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from backend.models import Task


app = FastAPI(title="Flunky_CLI")

logger.info("Starting FLUNKY backend application")
models.Base.metadata.create_all(bind=engine)
logger.info("Database tables ensured")


@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def user_registration(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info(
        "Registration attempt for username='%s', email='%s'",
        user.username,
        user.email
    )

    username_exist = db.query(models.User).filter(models.User.username == user.username).first()
    if username_exist is not None:
        logger.warning(
            "Registration failed: username already taken for username='%s'",
            user.username
        )
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )

    email_exist = db.query(models.User).filter(models.User.email == user.email).first()
    if email_exist is not None:
        logger.warning(
            "Registration failed: email already registered for email='%s'",
            user.email
        )
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    hashed_pass = hash_password(user.password)

    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pass
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(
        "User registered successfully: user_id=%s username='%s'",
        new_user.id,
        new_user.username
    )

    return new_user


@app.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    logger.info("Login attempt for username='%s'", form_data.username)

    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if user is None:
        logger.warning("Login failed: user not found for username='%s'", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not verify_password(form_data.password, user.hashed_password):
        logger.warning("Login failed: invalid password for username='%s'", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(data={"sub": user.username})

    logger.info(
        "Login successful for user_id=%s username='%s'",
        user.id,
        user.username
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.post("/tasks", response_model=schemas.TaskResponse, status_code=HTTP_201_CREATED)
def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    logger.info(
        "Create task request by user_id=%s username='%s'",
        current_user.id,
        current_user.username
    )

    new_task = Task(
        title=task.task_title,
        description=task.task_description,
        user_id=current_user.id
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    logger.info(
        "Task created: task_id=%s user_id=%s title='%s'",
        new_task.id,
        current_user.id,
        new_task.title
    )

    return new_task


@app.get("/tasks", response_model=list[schemas.TaskResponse])
def get_all_task(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    completed: bool = None
):
    logger.info(
        "Fetch tasks request by user_id=%s username='%s' completed_filter=%s",
        current_user.id,
        current_user.username,
        completed
    )

    task_query = db.query(models.Task).filter(models.Task.user_id == current_user.id)
    if completed is not None:
        task_query = task_query.filter(models.Task.is_completed == completed)

    tasks = task_query.all()

    logger.info(
        "Tasks fetched for user_id=%s completed_filter=%s count=%s",
        current_user.id,
        completed,
        len(tasks)
    )

    return tasks


@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    logger.info(
        "Fetch single task request: task_id=%s requested_by_user_id=%s",
        task_id,
        current_user.id
    )

    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    if task is None:
        logger.warning(
            "Task not found: task_id=%s requested_by_user_id=%s",
            task_id,
            current_user.id
        )
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id != current_user.id:
        logger.warning(
            "Unauthorized task access: task_id=%s owner_user_id=%s requested_by_user_id=%s",
            task.id,
            task.user_id,
            current_user.id
        )
        raise HTTPException(status_code=403, detail="Not authorized")

    logger.info(
        "Task fetched successfully: task_id=%s user_id=%s",
        task.id,
        current_user.id
    )

    return task


@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    logger.info(
        "Update task request: task_id=%s requested_by_user_id=%s",
        task_id,
        current_user.id
    )

    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    if task is None:
        logger.warning(
            "Update failed: task not found task_id=%s requested_by_user_id=%s",
            task_id,
            current_user.id
        )
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    if task.user_id != current_user.id:
        logger.warning(
            "Unauthorized task update: task_id=%s owner_user_id=%s requested_by_user_id=%s",
            task.id,
            task.user_id,
            current_user.id
        )
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this task"
        )

    if task_update.title is not None:
        task.title = task_update.title

    if task_update.description is not None:
        task.description = task_update.description

    if task_update.is_completed is not None:
        task.is_completed = task_update.is_completed

    db.commit()
    db.refresh(task)

    logger.info(
        "Task updated successfully: task_id=%s user_id=%s",
        task.id,
        current_user.id
    )

    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    logger.info(
        "Delete task request: task_id=%s requested_by_user_id=%s",
        task_id,
        current_user.id
    )

    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    if task is None:
        logger.warning(
            "Delete failed: task not found task_id=%s requested_by_user_id=%s",
            task_id,
            current_user.id
        )
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    if task.user_id != current_user.id:
        logger.warning(
            "Unauthorized task delete: task_id=%s owner_user_id=%s requested_by_user_id=%s",
            task.id,
            task.user_id,
            current_user.id
        )
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this task"
        )

    db.delete(task)
    db.commit()

    logger.info(
        "Task deleted successfully: task_id=%s user_id=%s",
        task.id,
        current_user.id
    )

    return None