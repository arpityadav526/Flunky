import secrets
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core import mail, rate_limit
from backend.core.config import settings
from backend.core.security import (
    DUMMY_HASH,
    aware,
    create_access_token,
    digest,
    hash_password,
    passwords,
    utcnow,
    verify_password,
)
from backend.models import AuthAction, AuthSession, User
from backend.schemas import Token


def unauthenticated() -> HTTPException:
    return HTTPException(
        401, "Invalid or revoked credentials", headers={"WWW-Authenticate": "Bearer"}
    )


async def authenticate(db: AsyncSession, username: str, password: str) -> User:
    key = "account:" + username.lower()
    rate_limit.limiter.check(key, 30, 900)
    user = await db.scalar(select(User).where(User.username == username))
    if not verify_password(password, user.hashed_password if user else DUMMY_HASH) or user is None:
        rate_limit.limiter.failure(key)
        raise HTTPException(401, "Invalid credentials")
    rate_limit.limiter.success(key)
    valid, replacement = passwords.verify_and_update(password, user.hashed_password)
    if replacement:
        user.hashed_password = replacement
    return user


async def issue_session(db: AsyncSession, user: User, family: str | None = None) -> Token:
    raw = secrets.token_urlsafe(48)
    session = AuthSession(
        id=str(uuid4()),
        family_id=family or str(uuid4()),
        user_id=user.id,
        token_hash=digest(raw),
        expires_at=utcnow() + timedelta(days=30),
    )
    db.add(session)
    await db.commit()
    return Token(
        access_token=create_access_token({"sub": user.username, "sid": session.id}),
        refresh_token=raw,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def revoke_family(db: AsyncSession, family: str) -> None:
    await db.execute(
        update(AuthSession).where(AuthSession.family_id == family).values(revoked=True)
    )
    await db.commit()


async def revoke_all(db: AsyncSession, user_id: int) -> None:
    await db.execute(update(AuthSession).where(AuthSession.user_id == user_id).values(revoked=True))
    await db.commit()


async def refresh(db: AsyncSession, raw: str) -> Token:
    session = await db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == digest(raw), AuthSession.kind == "refresh"
        )
    )
    if session is None or session.revoked or aware(session.expires_at) <= utcnow():
        raise unauthenticated()
    claimed = await db.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session.id,
            AuthSession.used.is_(False),
            AuthSession.revoked.is_(False),
        )
        .values(used=True)
        .returning(AuthSession.id)
    )
    if claimed.scalar_one_or_none() is None:
        await revoke_family(db, session.family_id)
        raise unauthenticated()
    user = await db.get(User, session.user_id)
    if user is None:
        raise unauthenticated()
    return await issue_session(db, user, session.family_id)


async def send_action(db: AsyncSession, user: User, kind: str) -> None:
    raw = secrets.token_urlsafe(48)
    db.add(
        AuthAction(
            token_hash=digest(raw),
            user_id=user.id,
            kind=kind,
            expires_at=utcnow() + timedelta(minutes=30),
        )
    )
    await db.commit()
    mail.mailer.send(user.email, kind, raw)


async def consume_action(db: AsyncSession, raw: str, kind: str) -> User:
    action = await db.get(AuthAction, digest(raw))
    if action is None or action.kind != kind or action.used or aware(action.expires_at) <= utcnow():
        raise HTTPException(400, "Invalid or expired action token")
    claimed = await db.execute(
        update(AuthAction)
        .where(AuthAction.token_hash == action.token_hash, AuthAction.used.is_(False))
        .values(used=True)
        .returning(AuthAction.token_hash)
    )
    if claimed.scalar_one_or_none() is None:
        raise HTTPException(400, "Action token already used")
    user = await db.get(User, action.user_id)
    if user is None:
        raise HTTPException(400, "Account unavailable")
    return user


async def change_password(db: AsyncSession, user: User, password: str) -> None:
    user.hashed_password = hash_password(password)
    await db.execute(
        update(AuthAction)
        .where(AuthAction.user_id == user.id, AuthAction.kind == "reset_password")
        .values(used=True)
    )
    await revoke_all(db, user.id)
