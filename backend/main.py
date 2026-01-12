
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from starlette.status import HTTP_201_CREATED
from tensorflow.python.distribute.multi_worker_util import task_count

# Your modules
from backend.database import engine, get_db
from backend import models, schemas
from backend.Auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from backend.models import Task

## APP INSTANCE ##
app = FastAPI(title="Flunky_CLI")
models.Base.metadata.create_all(bind=engine)


## USER REGISTRATION ##
@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def user_registration(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if username exists
    username_exist = db.query(models.User).filter(models.User.username == user.username).first()
    if username_exist is not None:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )

    # Check if email exists
    email_exist = db.query(models.User).filter(models.User.email == user.email).first()
    if email_exist is not None:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Hash password
    hashed_pass = hash_password(user.password)

    # Create new user
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pass
    )

    # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.post("/login", response_model=schemas.Token)
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    # Find user
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Create token
    access_token = create_access_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }



@app.post("/tasks", response_model=schemas.TaskResponse, status_code=HTTP_201_CREATED)
def create_task(
        task:schemas.TaskCreate,
        db:Session=Depends(get_db),
        current_user: models.User=Depends(get_current_user)

):


    new_task=Task(
        title=task.task_title,
        description=task.task_description,
        user_id=current_user.id
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task



@app.get("/tasks", response_model=list[schemas.TaskResponse])
def get_all_task(
        db: Session=Depends(get_db),
        current_user:models.User=Depends(get_current_user),
        completed: bool =None

):



    task_query=db.query(models.Task).filter(models.Task.user_id==current_user.id)
    if completed is not None:
        task_query=task_query.filter(models.Task.is_completed==completed)
    tasks=task_query.all()

    return tasks



@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    task_id_query=db.query(models.Task).filter(models.Task.id==task_id)
    if task_id_query is None:
        raise HTTPException(
            status_code=404 ,
            detail="Task not found"
        )

    if task_id_query.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this task"
        )

    return task_id_query


@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(
        task_id: int,
        task_update: schemas.TaskUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Get the task
    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    # Check if task exists
    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # Check ownership
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this task"
        )

    # Update only the fields that are provided (not None)
    if task_update.title is not None:
        task.title = task_update.title

    if task_update.description is not None:
        task.description = task_update.description

    if task_update.is_completed is not None:
        task.is_completed = task_update.is_completed

    # Save changes
    db.commit()
    db.refresh(task)

    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Get the task
    task = db.query(models.Task).filter(models.Task.id == task_id).first()

    # Check if task exists
    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # Check ownership
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this task"
        )

    # Delete the task
    db.delete(task)
    db.commit()

    return None  # 204 No Content doesn't return anything






















































































