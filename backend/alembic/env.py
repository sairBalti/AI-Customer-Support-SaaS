"""Alembic environment — SQLAlchemy 2.0 async (aiomysql / Settings.DATABASE_URL).

Uses ``Base.metadata`` from the application. Import the models package so
entity modules register for autogenerate once they exist.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Registers ORM tables on Base.metadata when entity models exist.
import app.infrastructure.database.models  # noqa: F401
from app.core.config import get_settings
from app.infrastructure.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve database URL from application settings."""
    return get_settings().database_url


def _escaped_url_for_config() -> str:
    """Escape percent signs for ConfigParser interpolation."""
    return get_url().replace("%", "%%")


config.set_main_option("sqlalchemy.url", _escaped_url_for_config())


def process_revision_directives(context_, revision, directives) -> None:  # noqa: ANN001, ARG001
    """Omit empty autogenerate revisions when metadata matches the database."""
    if getattr(context_.config.cmd_opts, "autogenerate", False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            print("No schema changes detected; skipping empty revision.")


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live database connection."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=False,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations on the sync connection provided by ``run_sync``."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=False,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Online path: async engine → sync migration bridge."""
    section = config.config_ini_section
    configuration = dict(config.get_section(section) or {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry for ``alembic upgrade`` / ``revision --autogenerate``."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
