"""
app/api/copilot.py
-------------------
API Router for AI Copilot Chat & Upload endpoints:
  - POST /api/v1/copilot/message
  - POST /api/v1/copilot/upload

Handles conversational intake extraction, field corrections, document attachments,
and atomic 21 CFR Part 11 audit logging (`ai_extraction` / `ai_correction`).
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import apply_correction, run_complaint_pipeline
from app.api.deps import get_actor
from app.core.audit import write_audit_log
from app.core.extraction import extract_text
from app.core.storage import UPLOAD_ROOT, save_upload
from app.db.session import generate_complaint_number, get_db
from app.models.ai_assessment import AIAssessment
from app.models.complaint import Complaint
from app.models.complaint_document import ComplaintDocument
from app.models.enums import RiskLevel
from app.schemas.copilot import (
    CopilotCorrectionResponse,
    CopilotMessageRequest,
    CopilotNewComplaintResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])


# ---------------------------------------------------------------------------
# POST /api/v1/copilot/message
# ---------------------------------------------------------------------------
@router.post(
    "/message",
    summary="Process a copilot chat message or field correction",
    response_model=None,
)
async def process_copilot_message(
    payload: CopilotMessageRequest,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_actor),
):
    """
    Handles conversational copilot messages:
      - complaint_id IS NULL     ➔ Run full AI intake pipeline, log new complaint + assessment, return confirmation.
      - complaint_id IS PRESENT  ➔ Run field correction agent, apply diff to complaint record, return confirmation.
    """
    # -----------------------------------------------------------------------
    # Case A: complaint_id IS PRESENT ➔ Field Correction
    # -----------------------------------------------------------------------
    if payload.complaint_id is not None:
        complaint = await db.get(Complaint, payload.complaint_id)
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID {payload.complaint_id} not found.",
            )

        existing_fields = _complaint_to_dict(complaint)
        correction_result = await apply_correction(
            existing_fields=existing_fields,
            correction_message=payload.message,
        )

        field_diff = correction_result.get("field_diff") or {}
        if field_diff:
            _apply_diff_to_complaint(complaint, field_diff)
            await db.flush()

            await write_audit_log(
                db,
                complaint_id=complaint.id,
                action="ai_correction",
                actor=actor,
                details={
                    "session_id": payload.session_id,
                    "field_diff": field_diff,
                    "correction_message": payload.message[:200],
                },
            )
            await db.commit()
            await db.refresh(complaint)

        reply_text = _build_correction_reply(complaint.complaint_number, field_diff)
        return CopilotCorrectionResponse(
            complaint_id=complaint.id,
            updated_fields=field_diff,
            reply_text=reply_text,
        )

    # -----------------------------------------------------------------------
    # Case B: complaint_id IS NULL ➔ New Complaint Intake
    # -----------------------------------------------------------------------
    pipeline_res = await run_complaint_pipeline(raw_text=payload.message, db_session=db)

    extracted = pipeline_res.get("extracted_fields") or {}
    sev = pipeline_res.get("severity") or pipeline_res.get("risk_level") or "major"
    next_action = pipeline_res.get("suggested_next_action") or "Initiate QA investigation."
    risk_assessment = pipeline_res.get("initial_risk_assessment") or pipeline_res.get("risk_rationale") or "Standard QA review."

    complaint_num = await generate_complaint_number(db)

    complaint = Complaint(
        complaint_number=complaint_num,
        complaint_source=extracted.get("complaint_source") or "email",
        customer_name=extracted.get("customer_name") or "Anonymous Reporter",
        complainant_contact=extracted.get("complainant_contact"),
        product_name=extracted.get("product_name") or "Unspecified Product",
        product_strength=extracted.get("product_strength"),
        batch_no=(extracted.get("batch_no") or "UNKNOWN").upper(),
        affected_quantity=extracted.get("affected_quantity"),
        manufacturing_date=_parse_date_safe(extracted.get("manufacturing_date")),
        expiry_date=_parse_date_safe(extracted.get("expiry_date")),
        originating_site_block=extracted.get("originating_site_block"),
        impacted_npm=extracted.get("impacted_npm"),
        complaint_category=extracted.get("complaint_category") or "quality",
        complaint_description=extracted.get("complaint_description") or payload.message,
        severity=sev,
        suggested_next_action=next_action,
        initial_risk_assessment=risk_assessment,
        status="ready_to_commit",
    )
    db.add(complaint)
    await db.flush()

    # Save AI Assessment record
    ai_assessment = AIAssessment(
        complaint_id=complaint.id,
        risk_level=_sev_to_risk_level(sev),
        risk_rationale=risk_assessment,
        completeness_flags=pipeline_res.get("completeness_flags"),
        root_cause_suggestion=pipeline_res.get("root_cause_suggestion"),
        capa_suggestion=pipeline_res.get("capa_suggestion"),
        summary=pipeline_res.get("summary"),
        raw_llm_output={"pipeline_state": pipeline_res},
    )
    db.add(ai_assessment)
    await db.flush()

    await write_audit_log(
        db,
        complaint_id=complaint.id,
        action="ai_extraction",
        actor=actor,
        details={
            "session_id": payload.session_id,
            "complaint_number": complaint_num,
            "product_name": complaint.product_name,
            "severity": sev,
        },
    )
    await db.commit()
    await db.refresh(complaint)

    reply_text = (
        f"Complaint {complaint_num} logged successfully. "
        f"Extracted product '{complaint.product_name}', batch '{complaint.batch_no}', "
        f"and assigned severity [{sev.upper()}]."
    )

    return CopilotNewComplaintResponse(
        complaint_id=complaint.id,
        complaint_number=complaint_num,
        extracted_fields=extracted,
        severity=sev,
        suggested_next_action=next_action,
        initial_risk_assessment=risk_assessment,
        reply_text=reply_text,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/copilot/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    summary="Upload document and run intake or field correction via copilot",
    response_model=None,
)
async def upload_copilot_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    complaint_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_actor),
):
    """
    Accepts a multipart file upload and performs AI intake or field correction.
    """
    temp_cid = complaint_id if complaint_id is not None else 0
    rel_path, file_size = await save_upload(file, temp_cid)
    abs_path = UPLOAD_ROOT / rel_path

    # Detect file type extension
    suffix = abs_path.suffix.lower().lstrip(".")
    detected_type = "pdf" if suffix == "pdf" else ("eml" if suffix == "eml" else "txt")

    loop = asyncio.get_running_loop()
    extracted_text = await loop.run_in_executor(None, extract_text, abs_path, detected_type) or ""

    if complaint_id is not None:
        # Case A: Correction on existing complaint
        complaint = await db.get(Complaint, complaint_id)
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID {complaint_id} not found.",
            )

        doc = ComplaintDocument(
            complaint_id=complaint.id,
            file_path=rel_path,
            file_type=file.content_type or detected_type,
            extracted_text=extracted_text,
        )
        db.add(doc)

        existing_fields = _complaint_to_dict(complaint)
        correction_result = await apply_correction(
            existing_fields=existing_fields,
            correction_message=extracted_text or file.filename or "",
        )
        field_diff = correction_result.get("field_diff") or {}
        if field_diff:
            _apply_diff_to_complaint(complaint, field_diff)

        await db.flush()
        await write_audit_log(
            db,
            complaint_id=complaint.id,
            action="ai_correction",
            actor=actor,
            details={
                "session_id": session_id,
                "file_name": file.filename,
                "field_diff": field_diff,
            },
        )
        await db.commit()
        await db.refresh(complaint)

        reply_text = _build_correction_reply(complaint.complaint_number, field_diff)
        return CopilotCorrectionResponse(
            complaint_id=complaint.id,
            updated_fields=field_diff,
            reply_text=reply_text,
        )

    # Case B: New Complaint from uploaded document
    input_text = extracted_text if len(extracted_text) > 10 else f"Complaint report from document: {file.filename}"
    pipeline_res = await run_complaint_pipeline(raw_text=input_text, db_session=db)

    extracted = pipeline_res.get("extracted_fields") or {}
    sev = pipeline_res.get("severity") or pipeline_res.get("risk_level") or "major"
    next_action = pipeline_res.get("suggested_next_action") or "Initiate QA investigation."
    risk_assessment = pipeline_res.get("initial_risk_assessment") or pipeline_res.get("risk_rationale") or "Standard QA review."

    complaint_num = await generate_complaint_number(db)

    complaint = Complaint(
        complaint_number=complaint_num,
        complaint_source=extracted.get("complaint_source") or "email",
        customer_name=extracted.get("customer_name") or "Anonymous Reporter",
        complainant_contact=extracted.get("complainant_contact"),
        product_name=extracted.get("product_name") or "Unspecified Product",
        product_strength=extracted.get("product_strength"),
        batch_no=(extracted.get("batch_no") or "UNKNOWN").upper(),
        affected_quantity=extracted.get("affected_quantity"),
        manufacturing_date=_parse_date_safe(extracted.get("manufacturing_date")),
        expiry_date=_parse_date_safe(extracted.get("expiry_date")),
        originating_site_block=extracted.get("originating_site_block"),
        impacted_npm=extracted.get("impacted_npm"),
        complaint_category=extracted.get("complaint_category") or "quality",
        complaint_description=extracted.get("complaint_description") or input_text[:500],
        severity=sev,
        suggested_next_action=next_action,
        initial_risk_assessment=risk_assessment,
        status="ready_to_commit",
    )
    db.add(complaint)
    await db.flush()

    doc = ComplaintDocument(
        complaint_id=complaint.id,
        file_path=rel_path,
        file_type=file.content_type or detected_type,
        extracted_text=extracted_text,
    )
    db.add(doc)

    ai_assessment = AIAssessment(
        complaint_id=complaint.id,
        risk_level=_sev_to_risk_level(sev),
        risk_rationale=risk_assessment,
        completeness_flags=pipeline_res.get("completeness_flags"),
        root_cause_suggestion=pipeline_res.get("root_cause_suggestion"),
        capa_suggestion=pipeline_res.get("capa_suggestion"),
        summary=pipeline_res.get("summary"),
        raw_llm_output={"pipeline_state": pipeline_res},
    )
    db.add(ai_assessment)
    await db.flush()

    await write_audit_log(
        db,
        complaint_id=complaint.id,
        action="ai_extraction",
        actor=actor,
        details={
            "session_id": session_id,
            "complaint_number": complaint_num,
            "file_name": file.filename,
            "severity": sev,
        },
    )
    await db.commit()
    await db.refresh(complaint)

    reply_text = (
        f"Document '{file.filename}' processed. "
        f"Logged complaint {complaint_num} ({complaint.product_name}, Lot {complaint.batch_no}) "
        f"with severity [{sev.upper()}]."
    )

    return CopilotNewComplaintResponse(
        complaint_id=complaint.id,
        complaint_number=complaint_num,
        extracted_fields=extracted,
        severity=sev,
        suggested_next_action=next_action,
        initial_risk_assessment=risk_assessment,
        reply_text=reply_text,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _complaint_to_dict(c: Complaint) -> Dict[str, Any]:
    return {
        "complaint_source": c.complaint_source.value if hasattr(c.complaint_source, "value") else c.complaint_source,
        "customer_name": c.customer_name,
        "complainant_contact": c.complainant_contact,
        "product_name": c.product_name,
        "product_strength": c.product_strength,
        "batch_no": c.batch_no,
        "affected_quantity": c.affected_quantity,
        "manufacturing_date": c.manufacturing_date.isoformat() if c.manufacturing_date else None,
        "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
        "originating_site_block": c.originating_site_block,
        "impacted_npm": c.impacted_npm,
        "complaint_category": c.complaint_category.value if hasattr(c.complaint_category, "value") else c.complaint_category,
        "complaint_description": c.complaint_description,
    }


def _apply_diff_to_complaint(c: Complaint, diff: Dict[str, Any]) -> None:
    for k, v in diff.items():
        if hasattr(c, k) and v is not None:
            if k == "batch_no" and isinstance(v, str):
                setattr(c, k, v.strip().upper())
            else:
                setattr(c, k, v)


def _sev_to_risk_level(sev: str) -> RiskLevel:
    s = (sev or "").strip().lower()
    if s == "critical":
        return RiskLevel.high
    elif s == "minor":
        return RiskLevel.low
    return RiskLevel.medium


def _build_correction_reply(num: str, diff: Dict[str, Any]) -> str:
    if not diff:
        return f"No fields were modified on complaint {num} from your message."

    changes = [f"{k} ('{v}')" for k, v in diff.items()]
    return f"Updated {len(diff)} field(s) on complaint {num}: " + ", ".join(changes) + "."


def _parse_date_safe(val: Any):
    if not val or not isinstance(val, str):
        return None
    try:
        return datetime.strptime(val.strip(), "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.strptime(val.strip(), "%m/%Y").date()
        except Exception:
            return None
