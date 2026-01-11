from dns.e164 import query
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.params import Depends
from sqlalchemy.orm import Session, session
from fastapi.security import OAuth2PasswordRequestForm

# Your modules
from backend.database import engine, get_db
from backend import models, schemas
from backend.Auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from backend.schemas import UserCreate

## APP INSTANCE ##
app = FastAPI(title="Flunky_CLI")
models.Base.metadata.create_all(bind=engine)


## USER REGISTRATION ##
@app.post("/register",response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED )
def user_registration(user:schemas.UserCreate, db: session = Depends(get_db)):
    ## CHECKING ID USERNAME EXIST OR NOT ##
     username_exist=db.query(models.User).filter(models.User.username == user.username).first()
     if username_exist is not None:
        raise HTTPException(
            status_code=400 ,
            detail="Username already taken"
        )
    ## CHECKING IF EMAIL EXIST OR NOT ##
    email_exist= db.query(models.User).filter(models.User.email==UserCreate.email).first()
    if email_exist is not None:
        raise HTTPException(
            status_code=400,
            detail="Email already linked! , choose another"
        )

    hashed_pass=hash_password(UserCreate.password)
    user_obj=models.User(
        username= user.username
        email=user.email
        hashed_password=user.hashed_pass

        )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

return user_obj


## LOGIN ENDPOINT ##

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm= Depends(), db :session= Depends(get_db)):
    find_user=db.query(models.User).filter(models.User.username == user.username)
    if find_user is not None:
        raise HTTPException(

        )






































































