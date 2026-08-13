"""
app/schemas/audit_log.py
-------------------------
Pydantic schemas for AuditLog (append-only audit trail).

Notes
-----
* AuditLogCreate is a narrow internal schema — audit entries are never created
  directly by end-users. A helper function (see below) should be called from
  service-layer functions whenever a complaint state changes.

* AuditLogResponse deliberately excludes any field that would allow a caller
  to infer that a record was modified — there are no updated_at fields because
  audit entries are immutable by design.

* details is typed as Optional[dict[str, Any]] — the JSONB payload is
  action-specific and not uniformly schema-able at the Pydantic layer.
  Consider narrower per-action schemas (StatusChangedDetails, etc.) in
  future iterations.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditLogCreate(BaseModel):
    """
    Internal schema for creating an audit log entry.
    Never exposed as a public API body — created programmatically by services.

    Usage example in a service function:
        log = AuditLogCreate(
            complaint_id=complaint.id,
            action="complaint.status_changed",
            actor=current_user.email,
            details={"from": old_status, "to": new_status},
        )
    """
    # complaint_id typically injected from context — not from client.
    complaint_id: int
    action: str = Field(
        ...,
        max_length=128,
        description=(
            "Dot-namespaced action label. "
            "e.g. 'complaint.status_changed', 'assessment.created', 'document.uploaded'."
        ),
    )
    actor: str = Field(
        ...,
        max_length=320,
        description=(
            "Identity of the actor. Use user email for humans, "
            "'system:ai-agent' or 'system:worker' for automated actions."
        ),
    )
    details: Optional[dict[str, Any]] = Field(
        None,
        description="Action-specific context payload. Schema varies by action type.",
    )


class AuditLogResponse(BaseModel):
    """
    Audit log entry as returned by GET /complaints/{id}/audit.
    Immutable — no update endpoints exist or should ever exist for audit logs.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    action: str
    actor: str
    details: Optional[dict[str, Any]]
    timestamp: datetime


class AuditLogListResponse(BaseModel):
    """Chronological list of audit entries for a complaint."""
    complaint_id: int
    entries: list[AuditLogResponse]
    total: int
