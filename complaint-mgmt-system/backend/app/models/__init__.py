"""
app/models/__init__.py
-----------------------
Single import point for all ORM models.
Import order matters here — Base must be imported before any model that
uses it, and models with FK dependencies must be imported after their
targets. The ordering below respects these constraints.

Importing all models here ensures that when Alembic's `env.py` does
`from app.models import *`, all tables are registered on Base.metadata
before `Base.metadata.create_all()` / autogenerate runs.
"""

from app.models.base import Base                              # noqa: F401
from app.models.enums import (                                # noqa: F401
    Category,
    RiskLevel,
    Severity,
    SourceType,
    Status,
)
from app.models.complaint import Complaint                    # noqa: F401
from app.models.complaint_document import ComplaintDocument   # noqa: F401
from app.models.ai_assessment import AIAssessment             # noqa: F401
from app.models.audit_log import AuditLog                     # noqa: F401

__all__ = [
    "Base",
    "Category",
    "RiskLevel",
    "Severity",
    "SourceType",
    "Status",
    "Complaint",
    "ComplaintDocument",
    "AIAssessment",
    "AuditLog",
]
