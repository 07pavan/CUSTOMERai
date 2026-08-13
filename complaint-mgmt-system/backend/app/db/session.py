"""
app/db/session.py
-----------------
Async SQLAlchemy engine, session factory, and FastAPI dependency.

Design notes
------------
* `expire_on_commit=False` — After a commit, ORM objects are NOT expired.
  Without this, accessing any attribute after `await db.commit()` would
  trigger an implicit lazy load, which fails in async context.

* `echo` is driven by DEBUG setting so SQL statements are logged in
  development but suppressed in production (where they'd flood log pipelines).

* `get_db` is typed as `AsyncGenerator[AsyncSession, None]` — FastAPI's
  Depends() will call it as an async context manager, yielding a session
  for the lifetime of a single request and closing it cleanly afterwards,
  even if an exception is raised.

* `generate_complaint_number` lives here (alongside the engine) because it
  needs a DB session and is a pure infrastructure concern, not business logic.
  It calls PostgreSQL's nextval() on the dedicated `complaint_number_seq`
  sequence created in migration 0001.
"""

from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}
if "postgresql" in settings.DATABASE_URL:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,     # See docstring — critical for async usage
    autocommit=False,
    autoflush=False,            # Explicit flush gives us control within a request
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async SQLAlchemy session for a single request.
    The session is rolled back on exception and always closed on exit.

    Usage in a router:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Complaint number generation
# ---------------------------------------------------------------------------
async def generate_complaint_number(db: AsyncSession) -> str:
    """
    Generate the next CMP-YYYY-NNNN complaint identifier.
    Uses PostgreSQL sequence if available, or COUNT fallback for SQLite.
    """
    try:
        seq: int = await db.scalar(text("SELECT nextval('complaint_number_seq')"))
    except Exception:
        cnt = await db.scalar(text("SELECT count(*) FROM complaints")) or 0
        seq = cnt + 1

    year = datetime.now(timezone.utc).year
    return f"CMP-{year}-{seq:04d}"
