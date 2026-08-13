"""
app/api/deps.py
---------------
Shared FastAPI dependencies extracted from individual routers so they can be
reused without creating circular imports between router modules.

Includes
--------
* get_actor      — resolves the acting user from X-Actor header
* get_complaint_or_404 — loads a Complaint with all relationships, raises 404

Design note: these were originally inline in complaints.py.  Moving them here
follows the FastAPI convention of a central `deps.py` module, which scales
cleanly as the number of routers grows.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.complaint import Complaint


# ---------------------------------------------------------------------------
# Actor resolution (placeholder for real JWT auth)
# ---------------------------------------------------------------------------

def get_actor(x_actor: Annotated[str | None, Header()] = None) -> str:
    """
    Resolve the acting user from the `X-Actor` HTTP header.

    Swap this out for a real JWT `get_current_user` dependency when auth is
    implemented — all router signatures remain identical.

    Dev usage:
        curl -H "X-Actor: qa.officer@pharma.com" ...
    """
    return x_actor or "anonymous"


# ---------------------------------------------------------------------------
# Complaint loader with 404 guard
# ---------------------------------------------------------------------------

async def get_complaint_or_404(
    complaint_id: int,
    db: AsyncSession = Depends(get_db),
) -> Complaint:
    """
    Fetch a Complaint by primary key with all child relationships eagerly loaded.
    Raises HTTP 404 if the complaint does not exist.

    Relationships loaded
    --------------------
    documents, assessments, audit_logs (via selectinload — each is a single
    extra query, not N+1).
    """
    stmt = (
        select(Complaint)
        .where(Complaint.id == complaint_id)
        .options(
            selectinload(Complaint.documents),
            selectinload(Complaint.assessments),
            selectinload(Complaint.audit_logs),
        )
    )
    complaint = await db.scalar(stmt)
    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id={complaint_id} not found.",
        )
    return complaint
