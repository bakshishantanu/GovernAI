from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

connect_args = {"statement_cache_size": 0} if "pooler.supabase.com" in settings.DATABASE_URL else {}

# Supabase's session-mode pooler (port 5432) caps a project at 15 concurrent
# clients, and that cap is shared by everyone connected to the project, not
# per-process. pool_size + max_overflow used to total exactly 15, so this one
# backend could claim the entire allowance on its own and the 16th checkout
# came back as a hard server error rather than a wait:
#
#     asyncpg.exceptions.InternalServerError: (EMAXCONNSESSION)
#     max clients reached in session mode - max clients are limited to pool_size: 15
#
# Capping our own total below the server's leaves room for a second developer
# running their own backend, and makes contention queue inside SQLAlchemy
# (which waits, then times out with a clear pool message) instead of surfacing
# as a 500 from Postgres.
#
# Worth knowing why this is reached so easily: GET /events/stream depends on
# get_db, and a request-scoped session lives as long as the request, so every
# open console tab pins one connection for as long as it stays open. Until
# that endpoint takes short-lived sessions of its own, tab count is effectively
# connection count.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=3,
    pool_timeout=10,
    # A pooled connection the server has already dropped otherwise resurfaces
    # as a mid-request failure; this checks liveness on checkout instead.
    pool_pre_ping=True,
    connect_args=connect_args,
)


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
