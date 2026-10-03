import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from backend.core.config import settings

passwords = PasswordHash((Argon2Hasher(), BcryptHasher()))
DUMMY_HASH = passwords.hash("not-a-real-password")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    return passwords.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return passwords.verify(password, hashed)
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict[str, Any]) -> str:
    payload = {
        **data,
        "iat": utcnow(),
        "exp": utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
        "iss": "flunky",
        "aud": "flunky-cli",
        "typ": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            issuer="flunky",
            audience="flunky-cli",
            options={"require": ["exp", "iat", "sub", "sid"]},
        )
        if payload.get("typ") != "access":
            raise jwt.InvalidTokenError()
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            401, "Session expired or invalid. Log in again.", headers={"WWW-Authenticate": "Bearer"}
        ) from None
