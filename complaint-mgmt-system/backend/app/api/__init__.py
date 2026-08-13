"""
app/api/__init__.py
-------------------
Aggregates all sub-routers into a single `api_router` that main.py includes.

Pattern: each resource gets its own file (complaints.py, documents.py, etc.).
This file collects them under a shared /api/v1 prefix so versioning is
controlled in one place — bump to /api/v2 here without touching individual
routers.
"""

from fastapi import APIRouter

from app.api.analytics   import router as analytics_router
from app.api.assessments import router as assessments_router
from app.api.complaints  import router as complaints_router
from app.api.documents   import router as documents_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(complaints_router)
api_router.include_router(documents_router)
api_router.include_router(assessments_router)
api_router.include_router(analytics_router)
