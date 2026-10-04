import os
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from backend.core.config import settings


class Base(DeclarativeBase):
    pass


if os.environ.get("VERCEL") and not settings.database_url.startswith("postgresql+asyncpg://"):
    raise RuntimeError("Vercel requires a persistent PostgreSQL DATABASE_URL.")

engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    **({"poolclass": NullPool} if os.environ.get("VERCEL") else {}),
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def sqlite_foreign_keys(connection: Any, record: Any) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
