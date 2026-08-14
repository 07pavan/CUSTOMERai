"""
app/api/complaints.py
----------------------
FastAPI router for the /complaints resource.

Endpoints
---------
POST   /complaints            Create a new complaint
GET    /complaints            List complaints with optional status/category filter
GET    /complaints/{id}       Full complaint detail (documents + assessments included)
PATCH  /complaints/{id}       Partial update of any mutable fields

Audit trail
-----------
Every mutating endpoint (POST, PATCH) writes a row to `audit_log` in the
same DB transaction as the complaint mutation, so they are always atomic.

Actor resolution
----------------
No authentication is implemented yet.  The `X-Actor` HTTP header is used to
identify who is making a change.  If omitted, defaults to "anonymous".
Replace this with a real JWT `current_user` dependency once auth is wired up.

Session handling
----------------
All endpoints receive an `AsyncSession` via `Depends(get_db)`.
We never call `session.commit()` inside helper functions — only at the
top-level endpoint, after all mutations are staged, to keep transactions
clean and atomic.

SQLAlchemy 2.0 patterns used
-----------------------------
* `select(Model).where(...)`  for queries
* `db.scalar(stmt)` / `db.scalars(stmt)` for result extraction
* `db.add(instance)` + `await db.commit()` for writes
* `await db.refresh(instance)` to reload relationships after commit
"""

import os
import tempfile
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.nodes.intake_parser import intake_parser_node
from app.core.audit import write_audit_log
from app.core.extraction import (
    extract_text_from_eml,
    extract_text_from_image,
    extract_text_from_pdf,
    extract_text_from_txt,
)
from app.api.deps import require_admin, require_user
from app.db.session import generate_complaint_number, get_db
from app.models.complaint import Complaint
from app.models.enums import Category, Status
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintListResponse,
    ComplaintListItem,
    ComplaintResponse,
    ComplaintUpdate,
    IntakeExtractResponse,
)

router = APIRouter(prefix="/complaints", tags=["Complaints"])

# ---------------------------------------------------------------------------
# Dependency: extract actor from header (placeholder for real auth)
# ---------------------------------------------------------------------------

def get_actor(x_actor: Annotated[str | None, Header()] = None) -> str:
    """
    Resolve the acting user from the `X-Actor` HTTP header.
    Swap this out for a JWT `current_user` dependency when auth is ready.

    Usage in curl:
        curl -H "X-Actor: qa.officer@pharma.com" ...
    """
    return x_actor or "anonymous"


# ---------------------------------------------------------------------------
# Shared query helper — load a complaint with all relationships eagerly
# ---------------------------------------------------------------------------

async def _get_complaint_or_404(
    complaint_id: int,
    db: AsyncSession,
) -> Complaint:
    """
    Fetch a complaint by PK with all child relationships loaded.
    Raises 404 HTTPException if not found.

    We use `selectinload` explicitly here (rather than relying on the model's
    `lazy="selectin"`) to ensure relationships are always loaded in a single
    query, even if the model default changes in the future.
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


# ===========================================================================
# POST /complaints — Create a new complaint
# ===========================================================================

@router.post(
    "/",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new complaint",
    description=(
        "Creates a complaint record from manually entered form fields. "
        "The complaint_number is auto-generated (CMP-YYYY-NNNN). "
        "Severity starts as NULL until the AI triage agent runs."
    ),
    dependencies=[Depends(require_user)],
)
async def create_complaint(
    payload: ComplaintCreate,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_actor),
) -> ComplaintResponse:
    # ------------------------------------------------------------------ #
    # 1. Generate the human-readable complaint number                     #
    # ------------------------------------------------------------------ #
    complaint_number = await generate_complaint_number(db)

    # ------------------------------------------------------------------ #
    # 2. Build the ORM instance                                            #
    # ------------------------------------------------------------------ #
    complaint = Complaint(
        complaint_number=complaint_number,
        product_name=payload.product_name,
        product_strength=payload.product_strength,
        batch_no=payload.batch_no,
        affected_quantity=payload.affected_quantity,
        manufacturing_date=payload.manufacturing_date,
        expiry_date=payload.expiry_date,
        originating_site_block=payload.originating_site_block,
        impacted_npm=payload.impacted_npm,
        customer_name=payload.customer_name,
        complainant_contact=payload.complainant_contact,
        complaint_source=payload.complaint_source,
        complaint_description=payload.complaint_description,
        complaint_category=payload.complaint_category,
        suggested_next_action=payload.suggested_next_action,
        initial_risk_assessment=payload.initial_risk_assessment,
        # severity: intentionally omitted — starts NULL (assessed by AI later)
        # status: uses server_default="new"
    )
    db.add(complaint)

    # ------------------------------------------------------------------ #
    # 3. Flush to obtain the complaint.id for the audit log FK            #
    # ------------------------------------------------------------------ #
    await db.flush()   # Sends INSERT to DB within current transaction; no commit yet.

    # ------------------------------------------------------------------ #
    # 4. Write audit entry (same transaction — atomic with the INSERT)    #
    # ------------------------------------------------------------------ #
    await write_audit_log(
        db,
        complaint_id=complaint.id,
        action="complaint.created",
        actor=actor,
        details={
            "complaint_number": complaint_number,
            "product_name": payload.product_name,
            "category": payload.category.value,
            "source_type": payload.source_type.value,
        },
    )

    # ------------------------------------------------------------------ #
    # 5. Commit and reload                                                 #
    # ------------------------------------------------------------------ #
    await db.commit()

    # Reload the full object with relationships (documents=[], assessments=[])
    complaint = await _get_complaint_or_404(complaint.id, db)
    return ComplaintResponse.model_validate(complaint)


# ===========================================================================
# GET /complaints — List complaints with filtering & pagination
# ===========================================================================

@router.get(
    "/",
    response_model=ComplaintListResponse,
    summary="List complaints",
    description=(
        "Returns a paginated list of complaints. "
        "Filter by `status` and/or `category` query parameters. "
        "Does NOT include nested documents or assessments (use /{id} for that)."
    ),
)
async def list_complaints(
    db: AsyncSession = Depends(get_db),
    # --- Filters ---
    status_filter: Optional[Status] = Query(
        None,
        alias="status",
        description="Filter by complaint lifecycle status.",
    ),
    category_filter: Optional[Category] = Query(
        None,
        alias="category",
        description="Filter by complaint category.",
    ),
    # --- Pagination ---
    page: int = Query(1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(
        20, ge=1, le=100, description="Items per page. Max 100."
    ),
) -> ComplaintListResponse:
    # ------------------------------------------------------------------ #
    # Build the base query                                                 #
    # ------------------------------------------------------------------ #
    base_stmt = select(Complaint)

    if status_filter is not None:
        base_stmt = base_stmt.where(Complaint.status == status_filter)

    if category_filter is not None:
        base_stmt = base_stmt.where(Complaint.category == category_filter)

    # ------------------------------------------------------------------ #
    # Count total (before pagination) for the pagination envelope         #
    # ------------------------------------------------------------------ #
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total: int = await db.scalar(count_stmt) or 0

    # ------------------------------------------------------------------ #
    # Paginated results — ordered by created_at DESC (newest first)       #
    # ------------------------------------------------------------------ #
    offset = (page - 1) * page_size
    items_stmt = (
        base_stmt
        .order_by(Complaint.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    # Lightweight list — no relationship eager loading needed here.
    result = await db.scalars(items_stmt)
    complaints = result.all()

    return ComplaintListResponse(
        items=[ComplaintListItem.model_validate(c) for c in complaints],
        total=total,
        page=page,
        page_size=page_size,
    )


# ===========================================================================
# GET /complaints/{id} — Full detail with documents and assessments
# ===========================================================================

@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Get complaint detail",
    description=(
        "Returns the full complaint record including linked documents "
        "and AI assessments (latest first)."
    ),
)
async def get_complaint(
    complaint_id: int,
    db: AsyncSession = Depends(get_db),
) -> ComplaintResponse:
    complaint = await _get_complaint_or_404(complaint_id, db)
    return ComplaintResponse.model_validate(complaint)


# ===========================================================================
# PATCH /complaints/{id} — Partial update
# ===========================================================================

@router.patch(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Update a complaint",
    description=(
        "Partially updates a complaint. Only the supplied fields are changed. "
        "`complaint_number`, `id`, and `created_at` are immutable. "
        "Every successful update writes an audit log entry detailing the before/after values."
    ),
)
async def update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_actor),
) -> ComplaintResponse:
    # ------------------------------------------------------------------ #
    # 1. Load existing complaint                                           #
    # ------------------------------------------------------------------ #
    complaint = await _get_complaint_or_404(complaint_id, db)

    # ------------------------------------------------------------------ #
    # 2. Compute the diff — only process fields the caller actually sent  #
    # ------------------------------------------------------------------ #
    # `payload.model_fields_set` contains only the keys explicitly set
    # by the caller (Pydantic v2). Fields omitted from the request body
    # are absent from this set, so we never accidentally overwrite them.
    update_data = payload.model_dump(include=payload.model_fields_set)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update were provided.",
        )

    # ------------------------------------------------------------------ #
    # 3. Detect changes and apply                                          #
    # ------------------------------------------------------------------ #
    changes: dict = {}
    is_status_change = False

    for field, new_value in update_data.items():
        old_value = getattr(complaint, field)

        # Convert enum instances to their .value for consistent comparison
        old_comparable = old_value.value if hasattr(old_value, "value") else old_value
        new_comparable = new_value.value if hasattr(new_value, "value") else new_value

        if old_comparable != new_comparable:
            changes[field] = {"from": old_comparable, "to": new_comparable}
            setattr(complaint, field, new_value)

            if field == "status":
                is_status_change = True

    # ------------------------------------------------------------------ #
    # 4. If nothing actually changed, return early (no write, no audit)   #
    # ------------------------------------------------------------------ #
    if not changes:
        # Re-validate and return the unchanged object
        return ComplaintResponse.model_validate(complaint)

    # ------------------------------------------------------------------ #
    # 5. Stamp updated_at explicitly                                       #
    # ------------------------------------------------------------------ #
    # `onupdate=func.now()` in the model is a server-side expression but
    # we stamp it in Python too for determinism in tests and refresh calls.
    complaint.updated_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------ #
    # 6. Write audit log (status changes get their own action label)      #
    # ------------------------------------------------------------------ #
    action = "complaint.status_changed" if is_status_change else "complaint.updated"

    await write_audit_log(
        db,
        complaint_id=complaint.id,
        action=action,
        actor=actor,
        details={"changes": changes},
    )

    # ------------------------------------------------------------------ #
    # 7. Commit and return refreshed record                                #
    # ------------------------------------------------------------------ #
    await db.commit()

    # Re-fetch to ensure relationships are current after the update.
    complaint = await _get_complaint_or_404(complaint.id, db)
    return ComplaintResponse.model_validate(complaint)


# ===========================================================================
# POST /complaints/extract — Fast-fill Form from Uploaded File/Snippet
# ===========================================================================

@router.post(
    "/extract",
    response_model=IntakeExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Fast-fill complaint form from uploaded document or text snippet",
    description=(
        "Accepts a document file (.pdf, .eml, .txt, image) or raw text snippet, "
        "runs the intake_parser AI node (gemma2-9b-it), and returns extracted form fields "
        "to pre-fill the intake form without writing to the database."
    ),
    dependencies=[Depends(require_user)],
)
async def extract_intake_fields(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
) -> IntakeExtractResponse:
    """
    Extract structured complaint intake fields from document or text before form submission.
    No DB records created.
    """
    extracted_text = ""

    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        content = await file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if ext == ".pdf":
                extracted_text = extract_text_from_pdf(tmp_path)
            elif ext in (".eml", ".msg"):
                extracted_text = extract_text_from_eml(tmp_path)
            elif ext in (".txt", ".log", ".csv"):
                extracted_text = extract_text_from_txt(tmp_path)
            elif ext in (".png", ".jpg", ".jpeg", ".tiff"):
                extracted_text = extract_text_from_image(tmp_path)
            else:
                extracted_text = content.decode("utf-8", errors="ignore")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    elif text and text.strip():
        extracted_text = text.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either a file upload or text parameter for extraction.",
        )

    if not extracted_text.strip():
        return IntakeExtractResponse(description="No text could be extracted from the document.")

    # Run intake_parser LangGraph node
    state = {"raw_text": extracted_text}
    state = await intake_parser_node(state)
    fields = state.get("extracted_fields", {})

    return IntakeExtractResponse(
        product_name=fields.get("product_name"),
        batch_no=fields.get("batch_no"),
        complainant_name=fields.get("complainant_name"),
        complainant_contact=fields.get("complainant_contact"),
        category=fields.get("category"),
        description=fields.get("description") or extracted_text[:1000],
        extracted_text=extracted_text,
    )

