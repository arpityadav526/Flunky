from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.Auth import create_access_token, hash_password, verify_password
from backend.database import get_db
from backend.models import User
from backend.schemas import Token, UserCreate, UserResponse

router = APIRouter(tags=["auth"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(value: UserCreate, db: DB) -> UserResponse:
    if await db.scalar(select(User).where(User.username == value.username)):
        raise HTTPException(400, "Username already taken")
    if await db.scalar(select(User).where(User.email == value.email)):
        raise HTTPException(400, "Email already registered")
    user = User(
        username=value.username,
        email=str(value.email),
        hashed_password=hash_password(value.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Username or email already registered") from None
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB) -> Token:
    user = await db.scalar(select(User).where(User.username == form.username))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token({"sub": user.username}), token_type="bearer")
