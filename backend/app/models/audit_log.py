"""
app/models/audit_log.py
------------------------
Immutable, append-only audit trail for all complaint-related actions.

Design decisions — 21 CFR Part 11 alignment
---------------------------------------------
* The table is intentionally INSERT-ONLY. There are NO updated_at columns and
  no update paths in the ORM. Rows must never be modified or deleted while the
  complaint is within its retention period (typically ≥1 year after product expiry
  under EU GMP Annex 11 / FDA 21 CFR Part 211).

* `timestamp` uses server_default=func.now() with timezone. This ensures the
  time is captured by PostgreSQL, not the application server, which matters in
  distributed / multi-region deployments where app clocks can skew.

* `actor` is a free-form string (not an FK to a users table) because:
    - We need to log system-generated actions (actor = "system:ai-agent").
    - User tables may be in an external IdP (Auth0, Okta) — storing the actor's
      string identity (e.g. email or sub claim) is safer than a nullable FK.

* `details` (JSONB) stores action-specific context, e.g.:
    - For status changes: {"from": "new", "to": "under_investigation"}
    - For AI assessments: {"assessment_id": 42, "risk_level": "high"}
    - For document uploads: {"document_id": 7, "file_type": "application/pdf"}
  JSONB is ideal here because each action type has a different schema.

* `action` is a short, machine-readable string. Suggested constants:
    "complaint.created"          "complaint.status_changed"
    "complaint.updated"          "assessment.created"
    "document.uploaded"          "document.text_extracted"
    "complaint.closed"           "duplicate.flagged"
  A separate ActionType enum was considered but rejected — audit log action
  vocabularies grow over time and a migration per new action would be excessive.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------ #
    # Foreign key                                                          #
    # ------------------------------------------------------------------ #
    complaint_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "complaints.id",
            ondelete="RESTRICT",   # Never silently delete audit history.
            name="fk_audit_log_complaint",
        ),
        nullable=False,
        index=True,
        comment=(
            "RESTRICT on delete: you must explicitly handle audit history "
            "before a complaint can be removed (e.g. archival process)."
        ),
    )

    # ------------------------------------------------------------------ #
    # Audit fields                                                         #
    # ------------------------------------------------------------------ #
    action: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment=(
            "Short machine-readable action label. "
            "e.g. 'complaint.status_changed', 'assessment.created', 'document.uploaded'. "
            "Dot-namespaced for easy prefix filtering."
        ),
    )

    actor: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        comment=(
            "Who performed the action. Use email/user-ID for human actors, "
            "'system:ai-agent' or 'system:worker' for automated processes."
        ),
    )

    # Action-specific structured context — see module docstring for examples.
    details: Mapped[Optional[Any]] = mapped_column(
        JSON_TYPE,
        nullable=True,
        comment="Action-specific JSONB/JSON payload. Schema varies per action type.",
    )

    # ------------------------------------------------------------------ #
    # Timestamp                                                            #
    # ------------------------------------------------------------------ #
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment=(
            "Set by PostgreSQL server clock (not app clock) for 21 CFR Part 11 "
            "compliant timestamping in distributed environments."
        ),
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    complaint: Mapped["Complaint"] = relationship(   # noqa: F821
        "Complaint",
        back_populates="audit_logs",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} "
            f"complaint_id={self.complaint_id} "
            f"action={self.action!r} "
            f"actor={self.actor!r}>"
        )


from app.models.complaint import Complaint  # noqa: E402, F401
