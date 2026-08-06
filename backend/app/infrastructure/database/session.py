"""Async SQLAlchemy engine, session factory, and DB helpers.

Engine creation does not open a MySQL connection. Connections are made only
when a session is used or when readiness/check helpers run explicitly.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine_kwargs() -> dict[str, Any]:
    settings = get_settings()
    return {
        "echo": settings.database_echo,
        "pool_pre_ping": True,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout,
        "pool_recycle": settings.database_pool_recycle,
        # Fail readiness/checkouts quickly when MySQL is unreachable.
        "connect_args": {
            "connect_timeout": settings.database_connect_timeout,
        },
    }


def get_engine() -> AsyncEngine:
    """Return the shared async engine, creating it lazily if needed.

    Creating the engine parses the URL and configures the pool; it does not
    connect to MySQL until the first checkout.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            **_build_engine_kwargs(),
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an ``AsyncSession``.

    Callers (application services / use cases) own commit and rollback.
    The session is always closed when the request scope ends.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> bool:
    """Return True if MySQL accepts a simple query; never raise to callers."""
    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def dispose_engine() -> None:
    """Dispose the engine and clear singletons (used on app shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
