"""
app/core/audit.py
-----------------
Lightweight helper for writing audit_log entries inside an open DB session.

Design contract
---------------
* `write_audit_log` is intentionally NOT async and does NOT commit.
  It only calls `db.add()` — the caller owns the transaction and must
  call `await db.commit()` (or `await db.flush()`) after.
  This ensures audit entries are always committed atomically with the
  change they describe — a failed commit rolls back both the change AND
  the audit row together, leaving no orphaned audit entries.

* The `actor` string convention:
    - Human users   → their email address or subject claim from JWT
    - API without auth (dev)  → value of `X-Actor` header, fallback "anonymous"
    - Background tasks / AI   → "system:ai-agent", "system:worker", etc.

* Common action labels (dot-namespaced for easy prefix queries):
    "complaint.created"
    "complaint.updated"          ← generic field changes
    "complaint.status_changed"   ← status changes get their own label
                                    because they are high-value audit events
    "document.uploaded"
    "assessment.created"
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    complaint_id: int,
    action: str,
    actor: str,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """
    Append an audit log entry to the current session (no commit).

    Parameters
    ----------
    db          : Open async session — caller owns the transaction.
    complaint_id: The complaint being acted on.
    action      : Dot-namespaced label, e.g. "complaint.status_changed".
    actor       : String identity of who performed the action.
    details     : Optional JSONB payload with action-specific context.

    Returns
    -------
    The (unflushed) AuditLog ORM instance, in case the caller needs its id.
    """
    entry = AuditLog(
        complaint_id=complaint_id,
        action=action,
        actor=actor,
        details=details,
    )
    db.add(entry)
    return entry
