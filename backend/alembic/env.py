"""
alembic/env.py
--------------
Alembic environment — supports BOTH sync (offline) and async (online) modes.

Key design decisions
---------------------
1. DATABASE_URL is read from the environment (via pydantic Settings), never
   from alembic.ini, so credentials stay out of version control.

2. We use asyncpg as the driver (DATABASE_URL = postgresql+asyncpg://...).
   Alembic's built-in `connection.run_sync` bridges async sessions to
   synchronous Alembic migration logic.

3. All models are imported via `app.models` so that Base.metadata has full
   knowledge of the schema before autogenerate runs. If you add a new model
   file, import it in app/models/__init__.py — no changes needed here.

4. `compare_type=True` in run_migrations_online ensures that Alembic detects
   column type changes (e.g. VARCHAR(100) -> VARCHAR(255)) during autogenerate,
   not just additions/deletions.

5. `include_schemas=False` — we use the default 'public' schema only. Set to
   True and configure `include_name` if you add multi-schema support later.

Running migrations
------------------
    # Apply all pending migrations
    alembic upgrade head

    # Generate a new migration from model changes
    alembic revision --autogenerate -m "describe_your_change"

    # Downgrade one step
    alembic downgrade -1

    # View current revision
    alembic current
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Load all ORM models so Base.metadata is fully populated before autogenerate.
# ---------------------------------------------------------------------------
from app.models import Base  # noqa: F401 — side-effect import (registers all tables)
from app.core.config import settings

# Alembic Config object — provides access to .ini values.
config = context.config

# Override sqlalchemy.url from settings (env var), not alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from the alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object used by autogenerate.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# OFFLINE mode — generates SQL scripts without a DB connection.
# Useful for review, staging deploys, or air-gapped environments.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# ONLINE (async) mode — connects to the database and runs migrations directly.
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    """Synchronous migration runner called inside run_sync."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations via run_sync."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # NullPool for migrations — don't reuse connections.
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
