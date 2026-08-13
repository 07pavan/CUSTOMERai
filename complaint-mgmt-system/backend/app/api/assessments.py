"""
app/api/assessments.py
-----------------------
FastAPI router for AI Triage Assessment endpoints.

Endpoints
---------
POST /api/v1/complaints/{id}/assess
    Runs the 7-node LangGraph AI triage agent pipeline against the complaint's
    description and all attached documents' extracted text.
    Persists the result to `ai_assessments`, updates complaint `severity`/`category`
    if previously NULL, writes an audit_log row, and returns the assessment JSON.

GET /api/v1/complaints/{id}/assessments
    Lists all historical AI assessment runs for a complaint (latest first).
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.graph import run_complaint_pipeline
from app.api.deps import get_actor, get_complaint_or_404
from app.core.audit import write_audit_log
from app.db.session import get_db
from app.models.ai_assessment import AIAssessment
from app.models.complaint import Complaint
from app.models.enums import Category, RiskLevel, Severity
from app.schemas.ai_assessment import AIAssessmentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["AI Assessments"])

# ---------------------------------------------------------------------------
# Mappings: AI Pipeline Output → DB Enum Types
# ---------------------------------------------------------------------------

_RISK_MAP: dict[str, RiskLevel] = {
    "critical": RiskLevel.high,
    "major":    RiskLevel.medium,
    "minor":    RiskLevel.low,
    "high":     RiskLevel.high,
    "medium":   RiskLevel.medium,
    "low":      RiskLevel.low,
}

_SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.critical,
    "major":    Severity.major,
    "minor":    Severity.minor,
    "high":     Severity.critical,
    "medium":   Severity.major,
    "low":      Severity.minor,
}


# ===========================================================================
# POST /complaints/{id}/assess — Run AI Triage Pipeline
# ===========================================================================

@router.post(
    "/{complaint_id}/assess",
    response_model=AIAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger AI triage assessment for a complaint",
    description=(
        "Executes the full 7-node LangGraph agent pipeline against the complaint's "
        "description and any attached document extracted text.\n\n"
        "Operations performed:\n"
        "1. Concatenates complaint description and attached document text.\n"
        "2. Executes LangGraph pipeline (intake_parser → completeness_checker → "
        "risk_classifier → duplicate_detector → root_cause_recommender → "
        "capa_recommender → summary_generator).\n"
        "3. Stores result in `ai_assessments` linked to the complaint.\n"
        "4. Updates complaint `severity` and/or `category` if previously NULL.\n"
        "5. Writes audit_log entry (`ai_assessment_run`).\n"
        "6. Returns the completed assessment record."
    ),
    responses={
        201: {"description": "AI assessment completed and saved successfully."},
        404: {"description": "Complaint not found."},
    },
)
async def run_assessment(
    complaint_id: int,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_actor),
) -> AIAssessmentResponse:
    """
    Run full AI triage assessment on a complaint.
    """
    # ── 1. Fetch complaint with attached documents ───────────────────────────
    complaint = await get_complaint_or_404(complaint_id, db)

    # ── 2. Construct combined raw text ──────────────────────────────────────
    doc_texts: list[str] = []
    if complaint.documents:
        for doc in complaint.documents:
            if doc.extracted_text and doc.extracted_text.strip():
                doc_texts.append(f"[Document Attachment: {doc.file_type}]\n{doc.extracted_text.strip()}")

    combined_parts = [f"Product: {complaint.product_name}\nBatch: {complaint.batch_no}\nDescription: {complaint.description}"]
    if doc_texts:
        combined_parts.append("\n\n--- ATTACHED DOCUMENTS ---\n\n" + "\n\n".join(doc_texts))

    full_raw_text = "\n\n".join(combined_parts)

    logger.info("Running AI triage pipeline for complaint %d (text len=%d)", complaint_id, len(full_raw_text))

    # ── 3. Execute LangGraph agent graph ────────────────────────────────────
    state = await run_complaint_pipeline(
        raw_text=full_raw_text,
        db_session=db,
        complaint_id=complaint_id,
        similarity_threshold=0.75,
    )

    # Extract pipeline outputs
    risk_level_raw = (state.get("risk_level") or "major").lower().strip()
    risk_rationale = state.get("risk_rationale") or "Standard automated triage assessment."
    completeness_flags = state.get("completeness_flags") or []
    possible_duplicates = state.get("possible_duplicates") or []
    root_cause_suggestion = state.get("root_cause_suggestion")
    capa_suggestion = state.get("capa_suggestion")
    summary = state.get("summary")

    # Map risk level to DB RiskLevel enum
    db_risk_level = _RISK_MAP.get(risk_level_raw, RiskLevel.medium)

    # Determine duplicate FK
    duplicate_of_id: Optional[int] = None
    if possible_duplicates and isinstance(possible_duplicates, list):
        first_match = possible_duplicates[0]
        if isinstance(first_match, dict) and "complaint_id" in first_match:
            duplicate_of_id = first_match["complaint_id"]

    # Raw LLM output for reproducibility / debugging
    raw_llm = {
        "extracted_fields": state.get("extracted_fields"),
        "completeness_flags": completeness_flags,
        "possible_duplicates": possible_duplicates,
        "risk_level_raw": risk_level_raw,
    }

    # ── 4. Create AIAssessment record ───────────────────────────────────────
    assessment = AIAssessment(
        complaint_id=complaint_id,
        duplicate_of_complaint_id=duplicate_of_id,
        risk_level=db_risk_level,
        risk_rationale=risk_rationale,
        completeness_flags=completeness_flags,
        root_cause_suggestion=root_cause_suggestion,
        capa_suggestion=capa_suggestion,
        summary=summary,
        raw_llm_output=raw_llm,
    )
    db.add(assessment)
    await db.flush()  # assign assessment.id

    # ── 5. Backfill complaint severity / category if previously NULL ─────────
    changes_made = {}
    if complaint.severity is None:
        new_severity = _SEVERITY_MAP.get(risk_level_raw, Severity.major)
        complaint.severity = new_severity
        changes_made["severity"] = new_severity.value

    extracted_fields = state.get("extracted_fields", {})
    if complaint.category is None or complaint.category == Category.other:
        extracted_cat = (extracted_fields.get("category") or "").lower().strip()
        if extracted_cat in Category.__members__:
            new_cat = Category[extracted_cat]
            complaint.category = new_cat
            changes_made["category"] = new_cat.value

    if changes_made:
        complaint.updated_at = datetime.now(timezone.utc)

    # ── 6. Write audit log entry ──────────────────────────────────────────────
    await write_audit_log(
        db,
        complaint_id=complaint_id,
        action="ai_assessment_run",
        actor=actor,
        details={
            "assessment_id": assessment.id,
            "risk_level": db_risk_level.value,
            "risk_level_raw": risk_level_raw,
            "completeness_flags_count": len(completeness_flags),
            "duplicates_found": len(possible_duplicates),
            "duplicate_of_complaint_id": duplicate_of_id,
            "backfilled_fields": changes_made,
        },
    )

    # ── 7. Commit transaction ────────────────────────────────────────────────
    await db.commit()

    logger.info("Completed AI assessment %d for complaint %d.", assessment.id, complaint_id)

    return AIAssessmentResponse.model_validate(assessment)


# ===========================================================================
# GET /complaints/{id}/assessments — List Historical Assessments
# ===========================================================================

@router.get(
    "/{complaint_id}/assessments",
    response_model=List[AIAssessmentResponse],
    summary="List historical AI assessments for a complaint",
    description="Returns all AI assessment runs for the specified complaint, ordered by created_at DESC.",
)
async def list_assessments(
    complaint_id: int,
    db: AsyncSession = Depends(get_db),
) -> List[AIAssessmentResponse]:
    """
    Fetch all assessment records for a complaint (latest first).
    """
    await get_complaint_or_404(complaint_id, db)

    stmt = (
        select(AIAssessment)
        .where(AIAssessment.complaint_id == complaint_id)
        .order_by(AIAssessment.created_at.desc())
    )
    result = await db.scalars(stmt)
    assessments = result.all()
    return [AIAssessmentResponse.model_validate(a) for a in assessments]
