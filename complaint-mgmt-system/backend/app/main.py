"""
app/main.py
-----------
FastAPI application entry point.

Startup order
-------------
1. FastAPI app is created with OpenAPI metadata.
2. CORS middleware is added (allow Vite dev server + any extra configured origins).
3. All API routers are included under /api/v1.
4. A bare health-check endpoint lives at GET / (outside /api/v1 for load-balancer probes).
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.db.session import engine
from app.models.base import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "Pharmaceutical Complaint Management System API.\n\n"
        "Backed by FastAPI · PostgreSQL/SQLite · LangGraph · Groq LLMs."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# `settings.ALLOWED_ORIGINS` includes http://localhost:5173 (Vite dev server)
# and http://127.0.0.1:5173 by default.  Add production origins in .env:
#   ALLOWED_ORIGINS=["https://complaints.yourcompany.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],   # Useful for paginated list endpoints
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_router)

# ---------------------------------------------------------------------------
# Health check (outside /api/v1 — intentional)
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"], summary="Health check")
async def root():
    """
    Minimal health probe.  Returns 200 OK if the app is running.
    Does NOT check DB connectivity — add a /health/db endpoint for that.
    """
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
        "docs": "/docs",
    }
