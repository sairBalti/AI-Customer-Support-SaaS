"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config.settings import get_settings
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db
from app.main import create_app

import app.infrastructure.database.models  # noqa: F401


@pytest.fixture(autouse=True)
def _enable_auth_header_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration/unit HTTP tests may use X-* identity headers."""
    monkeypatch.setenv("AUTH_HEADER_BYPASS", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def db_engine():
    """Isolated async engine. Override with ``TEST_DATABASE_URL`` for MySQL."""
    database_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine_kwargs: dict = {"future": True}
    if database_url.startswith("sqlite"):
        # Share one in-memory DB across connections (api_client + seed fixtures).
        from sqlalchemy.pool import StaticPool

        engine_kwargs.update(
            {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            }
        )
    engine = create_async_engine(database_url, **engine_kwargs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def api_client(db_engine) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    app = create_app()

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
