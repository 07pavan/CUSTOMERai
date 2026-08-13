"""
app/schemas/__init__.py
------------------------
Re-exports all Pydantic schemas for convenient single-import access in routes.
"""

from app.schemas.complaint import (             # noqa: F401
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
    ComplaintListItem,
    ComplaintListResponse,
    ComplaintDocumentSummary,
    AIAssessmentSummary,
)
from app.schemas.complaint_document import (    # noqa: F401
    ComplaintDocumentCreate,
    ComplaintDocumentResponse,
    ComplaintDocumentTextResponse,
)
from app.schemas.ai_assessment import (         # noqa: F401
    CompletenessFlag,
    AIAssessmentCreate,
    AIAssessmentResponse,
    AIAssessmentTriggerResponse,
)
from app.schemas.audit_log import (             # noqa: F401
    AuditLogCreate,
    AuditLogResponse,
    AuditLogListResponse,
)

__all__ = [
    # Complaint
    "ComplaintCreate", "ComplaintUpdate", "ComplaintResponse",
    "ComplaintListItem", "ComplaintListResponse",
    "ComplaintDocumentSummary", "AIAssessmentSummary",
    # Document
    "ComplaintDocumentCreate", "ComplaintDocumentResponse",
    "ComplaintDocumentTextResponse",
    # AI Assessment
    "CompletenessFlag", "AIAssessmentCreate",
    "AIAssessmentResponse", "AIAssessmentTriggerResponse",
    # Audit Log
    "AuditLogCreate", "AuditLogResponse", "AuditLogListResponse",
]
