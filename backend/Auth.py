"""Compatibility entry points backed by revocable sessions."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import (
    aware,
    decode_access_token,
    digest,
    utcnow,
)
from backend.core.security import (
    create_access_token as create_access_token,
)
from backend.core.security import (
    hash_password as hash_password,
)
from backend.core.security import (
    verify_password as verify_password,
)
from backend.database import get_db
from backend.models import AuthSession, User
from backend.services.auth import unauthenticated

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/login")


async def get_current_user(
    request: Request,
    token_str: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if token_str.startswith("flunky_pat_"):
        session = await db.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == digest(token_str), AuthSession.kind == "pat"
            )
        )
    else:
        payload = decode_access_token(token_str)
        session = await db.get(AuthSession, str(payload["sid"]))
    if session is None or session.revoked or aware(session.expires_at) <= utcnow():
        raise unauthenticated()
    user = await db.get(User, session.user_id)
    if user is None:
        raise unauthenticated()
    request.state.auth_session = session
    return user


def verify_token(token_str: str) -> str:
    payload = decode_access_token(token_str)
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise HTTPException(401, "Invalid credentials")
    return subject
