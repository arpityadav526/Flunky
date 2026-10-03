import secrets
from datetime import timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.Auth import get_current_user
from backend.core import rate_limit
from backend.core.security import aware, digest, hash_password, utcnow, verify_password
from backend.database import get_db
from backend.models import AuthAction, AuthSession, DeviceFlow, Task, User
from backend.schemas import (
    AccountDelete,
    ActionRequest,
    DevicePoll,
    EmailRequest,
    PasswordChange,
    PATRequest,
    RefreshRequest,
    ResetRequest,
    Token,
    UserCreate,
    UserResponse,
)
from backend.services import auth

router = APIRouter(tags=["auth"])
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def throttle(request: Request, action: str, limit: int = 20) -> None:
    host = request.client.host if request.client else "unknown"
    rate_limit.limiter.check(f"{action}:{host}", limit, 60)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(value: UserCreate, db: DB, request: Request) -> UserResponse:
    throttle(request, "register", 10)
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
    await auth.send_action(db, user, "verify_email")
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB, request: Request
) -> Token:
    throttle(request, "login")
    return await auth.issue_session(db, await auth.authenticate(db, form.username, form.password))


@router.post("/auth/refresh", response_model=Token)
async def refresh(value: RefreshRequest, db: DB, request: Request) -> Token:
    throttle(request, "refresh", 60)
    return await auth.refresh(db, value.refresh_token)


@router.post("/auth/logout", status_code=204)
async def logout(db: DB, user: CurrentUser, request: Request, everywhere: bool = False) -> Response:
    if everywhere:
        await auth.revoke_all(db, user.id)
    else:
        await auth.revoke_family(db, request.state.auth_session.family_id)
    return Response(status_code=204)


@router.get("/auth/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/auth/verify-email")
async def verify_email(value: ActionRequest, db: DB, request: Request) -> dict[str, str]:
    throttle(request, "verify")
    user = await auth.consume_action(db, value.token, "verify_email")
    user.email_verified = True
    await db.commit()
    return {"status": "verified"}


@router.post("/auth/resend-verification", status_code=202)
async def resend_verification(db: DB, user: CurrentUser, request: Request) -> dict[str, str]:
    throttle(request, "resend", 5)
    if not user.email_verified:
        await auth.send_action(db, user, "verify_email")
    return {"status": "accepted"}


@router.post("/auth/password-reset", status_code=202)
async def request_reset(value: EmailRequest, db: DB, request: Request) -> dict[str, str]:
    throttle(request, "reset", 5)
    user = await db.scalar(select(User).where(User.email == value.email))
    if user:
        await auth.send_action(db, user, "reset_password")
    return {"status": "accepted"}


@router.post("/auth/password-reset/confirm")
async def confirm_reset(value: ResetRequest, db: DB, request: Request) -> dict[str, str]:
    throttle(request, "reset-confirm", 10)
    user = await auth.consume_action(db, value.token, "reset_password")
    await auth.change_password(db, user, value.password)
    return {"status": "password_changed"}


@router.post("/auth/change-password")
async def change_password(
    value: PasswordChange, db: DB, user: CurrentUser, request: Request
) -> dict[str, str]:
    throttle(request, "change-password", 5)
    if not verify_password(value.current_password, user.hashed_password):
        raise auth.unauthenticated()
    await auth.change_password(db, user, value.new_password)
    return {"status": "password_changed"}


@router.delete("/auth/account", status_code=204)
async def delete_account(
    value: AccountDelete, db: DB, user: CurrentUser, request: Request
) -> Response:
    throttle(request, "delete-account", 5)
    if not verify_password(value.password, user.hashed_password):
        raise auth.unauthenticated()
    for model in (AuthSession, AuthAction, DeviceFlow, Task):
        await db.execute(delete(model).where(model.user_id == user.id))
    await db.delete(user)
    await db.commit()
    return Response(status_code=204)


@router.post("/auth/tokens", status_code=201)
async def create_pat(value: PATRequest, db: DB, user: CurrentUser) -> dict[str, str]:
    if not user.email_verified:
        raise HTTPException(403, "Verify your email before creating automation tokens")
    raw = "flunky_pat_" + secrets.token_urlsafe(48)
    session_id = str(uuid4())
    db.add(
        AuthSession(
            id=session_id,
            family_id=session_id,
            user_id=user.id,
            kind="pat",
            name=value.name,
            token_hash=digest(raw),
            expires_at=utcnow() + timedelta(days=value.expires_days),
        )
    )
    await db.commit()
    return {"id": session_id, "token": raw, "name": value.name}


@router.get("/auth/tokens")
async def list_pats(db: DB, user: CurrentUser) -> list[dict[str, str | bool]]:
    rows = await db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.kind == "pat")
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "revoked": row.revoked,
            "expires_at": row.expires_at.isoformat(),
        }
        for row in rows
    ]


@router.delete("/auth/tokens/{token_id}", status_code=204)
async def revoke_pat(token_id: str, db: DB, user: CurrentUser) -> Response:
    session = await db.get(AuthSession, token_id)
    if session is None or session.user_id != user.id or session.kind != "pat":
        raise HTTPException(404, "Token not found")
    session.revoked = True
    await db.commit()
    return Response(status_code=204)


@router.post("/auth/device")
async def start_device(db: DB, request: Request) -> dict[str, str | int]:
    throttle(request, "device", 10)
    raw = secrets.token_urlsafe(48)
    code = secrets.token_hex(4).upper()
    db.add(
        DeviceFlow(
            token_hash=digest(raw), user_code=code, expires_at=utcnow() + timedelta(minutes=10)
        )
    )
    await db.commit()
    return {
        "device_code": raw,
        "user_code": code,
        "verification_uri": str(request.base_url).rstrip("/") + "/v1/auth/device/verify",
        "expires_in": 600,
        "interval": 5,
    }


@router.get("/auth/device/verify", response_class=HTMLResponse)
async def device_page() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Approve Flunky</title><body><main><h1>Approve a Flunky sign-in</h1><p>Only approve the code shown in your own terminal. Never approve a code sent by someone else.</p><form method="post"><p><label>Terminal code <input name="code" required maxlength="12" autocomplete="off"></label></p><p><label>Username <input name="username" required autocomplete="username"></label></p><p><label>Password <input name="password" type="password" required autocomplete="current-password"></label></p><button>Approve sign-in</button></form></main></body></html>""",
        headers={
            "Content-Security-Policy": "default-src 'none'; form-action 'self'; frame-ancestors 'none'",
            "Cache-Control": "no-store",
        },
    )


@router.post("/auth/device/verify", response_class=HTMLResponse)
async def approve_device(
    db: DB,
    request: Request,
    code: Annotated[str, Form(max_length=12)],
    username: Annotated[str, Form(max_length=50)],
    password: Annotated[str, Form(max_length=1024)],
) -> HTMLResponse:
    throttle(request, "device-approve", 10)
    user = await auth.authenticate(db, username, password)
    flow = await db.scalar(select(DeviceFlow).where(DeviceFlow.user_code == code.upper()))
    if (
        flow is None
        or flow.consumed
        or flow.user_id is not None
        or aware(flow.expires_at) <= utcnow()
    ):
        raise HTTPException(400, "Invalid or expired device code")
    flow.user_id = user.id
    await db.commit()
    return HTMLResponse(
        "<h1>Sign-in approved</h1><p>Return to your terminal.</p>",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/auth/device/token", response_model=Token)
async def poll_device(value: DevicePoll, db: DB, request: Request) -> Token:
    throttle(request, "device-poll", 30)
    flow = await db.get(DeviceFlow, digest(value.device_code))
    if flow is None or flow.consumed or aware(flow.expires_at) <= utcnow():
        raise HTTPException(400, "expired_token")
    if flow.last_poll and (utcnow() - aware(flow.last_poll)).total_seconds() < 5:
        raise HTTPException(429, "slow_down", headers={"Retry-After": "5"})
    flow.last_poll = utcnow()
    if flow.user_id is None:
        await db.commit()
        raise HTTPException(400, "authorization_pending")
    claimed = await db.execute(
        update(DeviceFlow)
        .where(DeviceFlow.token_hash == flow.token_hash, DeviceFlow.consumed.is_(False))
        .values(consumed=True)
        .returning(DeviceFlow.token_hash)
    )
    if claimed.scalar_one_or_none() is None:
        raise HTTPException(400, "expired_token")
    user = await db.get(User, flow.user_id)
    if user is None:
        raise auth.unauthenticated()
    return await auth.issue_session(db, user)
