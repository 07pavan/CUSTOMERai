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
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import apply_correction, run_complaint_pipeline
from app.agents.llm import acall_llama
from app.api.deps import get_actor, require_user
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
# Helper functions
# ---------------------------------------------------------------------------
def _is_clear_intent(text: str) -> bool:
    """Returns True if the user asks to clear or reset the form/chat."""
    cleaned = (text or "").strip().lower()
    clear_phrases = {
        "clear", "reset", "clear form", "reset form", "clear chat", "reset chat",
        "start over", "new complaint", "clean form", "erase", "delete form",
        "clear all", "reset all",
    }
    return cleaned in clear_phrases or any(cleaned.startswith(p) for p in clear_phrases)


def _sync_manual_form_edits(complaint: Complaint, manual_fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Syncs manual edits made on the frontend form directly into the Complaint model.
    Returns the dictionary of fields synced.
    """
    if not manual_fields or not isinstance(manual_fields, dict):
        return {}

    synced = {}
    field_map = {
        "customer_name":          lambda v: str(v).strip(),
        "complainant_contact":    lambda v: str(v).strip() or None,
        "product_name":           lambda v: str(v).strip(),
        "product_strength":       lambda v: str(v).strip() or None,
        "batch_no":               lambda v: str(v).strip().upper(),
        "affected_quantity":      lambda v: str(v).strip() or None,
        "manufacturing_date":     lambda v: _parse_date_safe(str(v)),
        "expiry_date":            lambda v: _parse_date_safe(str(v)),
        "originating_site_block": lambda v: str(v).strip() or None,
        "impacted_npm":           lambda v: str(v).strip() or None,
        "complaint_category":     lambda v: str(v).strip().lower() or "quality",
        "complaint_description":  lambda v: str(v).strip(),
        "severity":               lambda v: str(v).strip().lower() or None,
        "suggested_next_action":  lambda v: str(v).strip() or None,
        "initial_risk_assessment":lambda v: str(v).strip() or None,
    }

    for key, transform in field_map.items():
        if key in manual_fields:
            val = manual_fields[key]
            if val is not None and str(val).strip() != "":
                parsed = transform(val)
                curr = getattr(complaint, key, None)
                if parsed != curr and parsed is not None:
                    setattr(complaint, key, parsed)
                    synced[key] = parsed

    return synced


# ---------------------------------------------------------------------------
# POST /api/v1/copilot/message
# ---------------------------------------------------------------------------
@router.post(
    "/message",
    response_model=Union[CopilotNewComplaintResponse, CopilotCorrectionResponse],
    summary="Process conversational message from AI Copilot panel",
    description=(
        "Dual-purpose endpoint for the Copilot conversational sidebar: "
        "if `complaint_id` is null, runs intake triage pipeline; "
        "if `complaint_id` is provided, syncs manual form edits, runs corrections, or answers QA queries."
    ),
    dependencies=[Depends(require_user)],
)
async def process_copilot_message(
    payload: CopilotMessageRequest,
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_actor),
):
    """
    Handles conversational copilot messages:
      - message is "clear"/"reset" ➔ Return action=clear to reset form & chat.
      - message is "submit"/"commit" ➔ Return action=submit to trigger form submission.
      - complaint_id IS PRESENT  ➔ Sync manual edits, run field correction or QA guidance.
      - complaint_id IS NULL     ➔ Run full AI intake pipeline or conversational QA guidance.
    """
    # -----------------------------------------------------------------------
    # Case 0A: User wants to clear / reset form
    # -----------------------------------------------------------------------
    if _is_clear_intent(payload.message):
        return CopilotCorrectionResponse(
            complaint_id=None,
            updated_fields={},
            reply_text="🗑️ Form and chat cleared. You can start a fresh complaint intake now.",
            action="clear",
        )

    # -----------------------------------------------------------------------
    # Case 0B: User wants to submit the complaint via chat
    # -----------------------------------------------------------------------
    if payload.complaint_id is not None and _is_submit_intent(payload.message):
        complaint = await db.get(Complaint, payload.complaint_id)
        if complaint:
            if payload.current_form_fields:
                _sync_manual_form_edits(complaint, payload.current_form_fields)
                await db.flush()

            missing_prompt = _get_missing_fields_prompt(complaint)
            all_complete = "All key QA fields are now complete" in missing_prompt
            if all_complete:
                return CopilotCorrectionResponse(
                    complaint_id=complaint.id,
                    updated_fields={},
                    reply_text="✅ Form is complete! Submitting to QMS Ledger now...",
                    action="submit",
                )
            else:
                return CopilotCorrectionResponse(
                    complaint_id=complaint.id,
                    updated_fields={},
                    reply_text=f"⚠️ Cannot submit yet — there are still missing fields.{missing_prompt}",
                )

    # -----------------------------------------------------------------------
    # Case A: complaint_id IS PRESENT ➔ Sync Manual Edits + Run Correction/QA Agent
    # -----------------------------------------------------------------------
    if payload.complaint_id is not None:
        complaint = await db.get(Complaint, payload.complaint_id)
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID {payload.complaint_id} not found.",
            )

        # 1. Sync manual form edits made on frontend form
        if payload.current_form_fields:
            _sync_manual_form_edits(complaint, payload.current_form_fields)
            await db.flush()

        # Build history list from request payload
        history = [
            {"role": m.role, "content": m.content}
            for m in (payload.chat_history or [])
        ]

        # 2. Conversational query / general question / QA assistance
        if _is_conversational_query(payload.message):
            reply = await _generate_conversational_reply(
                complaint=complaint,
                user_message=payload.message,
                chat_history=history,
                current_form=payload.current_form_fields,
            )
            return CopilotCorrectionResponse(
                complaint_id=complaint.id,
                updated_fields={},
                reply_text=reply,
            )

        # 3. Field correction / update diff
        existing_fields = _complaint_to_dict(complaint)
        correction_result = await apply_correction(
            existing_fields=existing_fields,
            correction_message=payload.message,
            chat_history=history,
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

        field_diff_normalized = _normalize_diff_for_frontend(field_diff)
        reply_text = _build_correction_reply(complaint, field_diff)
        return CopilotCorrectionResponse(
            complaint_id=complaint.id,
            updated_fields=field_diff_normalized,
            reply_text=reply_text,
        )

    # -----------------------------------------------------------------------
    # Case B: complaint_id IS NULL ➔ decide between chat vs. intake pipeline
    # -----------------------------------------------------------------------

    # Pure greeting / no-data message → welcome reply, with awareness of manual form values
    if _is_greeting_message(payload.message):
        reply = await _generate_initial_reply(
            user_message=payload.message,
            chat_history=[
                {"role": m.role, "content": m.content}
                for m in (payload.chat_history or [])
            ],
            current_form=payload.current_form_fields,
        )
        return CopilotNewComplaintResponse(reply_text=reply)

    # Conversational questions, requests, or instructions (not new complaint intake text)
    if _is_conversational_query(payload.message) or not _has_complaint_substance(payload.message):
        reply = await _generate_initial_reply(
            user_message=payload.message,
            chat_history=[
                {"role": m.role, "content": m.content}
                for m in (payload.chat_history or [])
            ],
            current_form=payload.current_form_fields,
        )
        return CopilotNewComplaintResponse(reply_text=reply)

    # Has real complaint data → run the full triage pipeline
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

    full_extracted = {
        "complaint_source": complaint.complaint_source,
        "customer_name": complaint.customer_name,
        "complainant_contact": complaint.complainant_contact,
        "product_name": complaint.product_name,
        "product_strength": complaint.product_strength,
        "batch_no": complaint.batch_no,
        "affected_quantity": complaint.affected_quantity,
        "manufacturing_date": str(complaint.manufacturing_date) if complaint.manufacturing_date else extracted.get("manufacturing_date"),
        "expiry_date": str(complaint.expiry_date) if complaint.expiry_date else extracted.get("expiry_date"),
        "originating_site_block": complaint.originating_site_block,
        "impacted_npm": complaint.impacted_npm,
        "complaint_category": complaint.complaint_category,
        "complaint_description": complaint.complaint_description,
        "severity": complaint.severity,
        "suggested_next_action": complaint.suggested_next_action,
        "initial_risk_assessment": complaint.initial_risk_assessment,
    }

    reply_text = _build_intake_reply(complaint, complaint_num, sev, next_action, risk_assessment)

    return CopilotNewComplaintResponse(
        complaint_id=complaint.id,
        complaint_number=complaint_num,
        extracted_fields=full_extracted,
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
    dependencies=[Depends(require_user)],
)
async def upload_copilot_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    complaint_id: Optional[Any] = Form(None),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_actor),
):
    """
    Accepts a multipart file upload and performs AI intake or field correction.
    """
    session_id_str = str(session_id).strip() if session_id else "default_session"
    cid_val: Optional[int] = None
    if complaint_id not in (None, "", "null", "undefined"):
        try:
            parsed_cid = int(complaint_id)
            if parsed_cid > 0:
                cid_val = parsed_cid
        except (ValueError, TypeError):
            cid_val = None

    temp_cid = cid_val if cid_val is not None else 0
    rel_path, file_size = await save_upload(file, temp_cid)
    abs_path = UPLOAD_ROOT / rel_path

    # Detect file type extension
    suffix = abs_path.suffix.lower().lstrip(".")
    detected_type = "pdf" if suffix == "pdf" else ("eml" if suffix == "eml" else "txt")

    loop = asyncio.get_running_loop()
    extracted_text = await loop.run_in_executor(None, extract_text, abs_path, detected_type) or ""

    if cid_val is not None:
        # Case A: Correction on existing complaint
        complaint = await db.get(Complaint, cid_val)
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

        reply_text = _build_correction_reply(complaint, field_diff)
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

    full_extracted = {
        "complaint_source": complaint.complaint_source,
        "customer_name": complaint.customer_name,
        "complainant_contact": complaint.complainant_contact,
        "product_name": complaint.product_name,
        "product_strength": complaint.product_strength,
        "batch_no": complaint.batch_no,
        "affected_quantity": complaint.affected_quantity,
        "manufacturing_date": str(complaint.manufacturing_date) if complaint.manufacturing_date else extracted.get("manufacturing_date"),
        "expiry_date": str(complaint.expiry_date) if complaint.expiry_date else extracted.get("expiry_date"),
        "originating_site_block": complaint.originating_site_block,
        "impacted_npm": complaint.impacted_npm,
        "complaint_category": complaint.complaint_category,
        "complaint_description": complaint.complaint_description,
        "severity": complaint.severity,
        "suggested_next_action": complaint.suggested_next_action,
        "initial_risk_assessment": complaint.initial_risk_assessment,
    }

    reply_text = (
        f"📄 **{file.filename}** extracted successfully.\n"
        + _build_intake_reply(complaint, complaint_num, sev, next_action, risk_assessment)
    )

    return CopilotNewComplaintResponse(
        complaint_id=complaint.id,
        complaint_number=complaint_num,
        extracted_fields=full_extracted,
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
    """Apply a field diff dict to a Complaint model, with proper type coercion for dates."""
    for k, v in diff.items():
        if hasattr(c, k) and v is not None:
            if k == "batch_no" and isinstance(v, str):
                setattr(c, k, v.strip().upper())
            elif k in ("manufacturing_date", "expiry_date"):
                # Always parse through our robust date parser so raw strings like
                # "2025/2/25" or "2026/feb/2" are safely converted to date objects.
                parsed = _parse_date_safe(str(v))
                if parsed is not None:
                    setattr(c, k, parsed)
                # If unparseable, leave the existing value unchanged.
            else:
                setattr(c, k, v)


def _normalize_diff_for_frontend(diff: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert raw date strings in a field diff to ISO YYYY-MM-DD format so that
    HTML <input type="date"> elements display them correctly in the React form.
    Non-date fields are passed through unchanged.
    """
    out = {}
    for k, v in diff.items():
        if k in ("manufacturing_date", "expiry_date") and isinstance(v, str):
            parsed = _parse_date_safe(v)
            out[k] = parsed.isoformat() if parsed else v
        else:
            out[k] = v
    return out


def _sev_to_risk_level(sev: str) -> RiskLevel:
    s = (sev or "").strip().lower()
    if s == "critical":
        return RiskLevel.high
    elif s == "minor":
        return RiskLevel.low
    return RiskLevel.medium


def _get_missing_fields_prompt(c: Complaint) -> str:
    missing_labels = []
    if not c.customer_name or c.customer_name.strip() in {"Anonymous Reporter", "null", ""}:
        missing_labels.append("Customer/Reporter Name")
    if not c.product_name or c.product_name.strip() in {"Unspecified Product", "null", ""}:
        missing_labels.append("Product Name")
    if not c.product_strength:
        missing_labels.append("Product Strength / Grade (e.g., 500mg, 10mg/mL)")
    if not c.batch_no or c.batch_no.strip() in {"UNKNOWN", "null", ""}:
        missing_labels.append("Batch / Lot Number")
    if not c.affected_quantity:
        missing_labels.append("Affected Quantity (e.g., 48 capsules, 3 vials)")
    if not c.expiry_date:
        missing_labels.append("Expiry Date (e.g., 2028-02-28 or 02/2028)")

    if not missing_labels:
        return "\n\n✨ All key QA fields are now complete! You can review the form on the left and click 'Commit to QMS Ledger'."

    return "\n\n📌 **Missing Details Needed**:\nCould you please tell me:\n• " + "\n• ".join(missing_labels) + "\n\n*(You can reply naturally, e.g. 'Customer is Apollo Pharmacy and quantity is 48 capsules')*"


# Human-readable labels for field names shown in AI replies
_FIELD_LABELS = {
    "complaint_source": "Source",
    "customer_name": "Customer / Reporter",
    "complainant_contact": "Contact",
    "product_name": "Product Name",
    "product_strength": "Product Strength",
    "batch_no": "Batch / Lot Number",
    "affected_quantity": "Affected Quantity",
    "manufacturing_date": "Manufacturing Date",
    "expiry_date": "Expiry Date",
    "originating_site_block": "Site / Block",
    "impacted_npm": "Impacted NPM",
    "complaint_category": "Category",
    "complaint_description": "Description",
    "severity": "Severity",
    "suggested_next_action": "Suggested Action",
    "initial_risk_assessment": "Risk Assessment",
}


def _build_intake_reply(c: Complaint, num: str, sev: str, next_action: str, risk_assessment: str) -> str:
    """
    Rich formatted reply shown after first complaint creation.
    Lists exactly what was extracted and asks for missing fields — as per assignment spec.
    """
    placeholder_values = {"anonymous reporter", "unspecified product", "unknown", "null", ""}

    filled = []
    if c.customer_name and c.customer_name.strip().lower() not in placeholder_values:
        filled.append(f"**Customer**: {c.customer_name}")
    if c.product_name and c.product_name.strip().lower() not in placeholder_values:
        filled.append(f"**Product**: {c.product_name}")
    if c.product_strength:
        filled.append(f"**Strength**: {c.product_strength}")
    if c.batch_no and c.batch_no.strip().lower() not in placeholder_values:
        filled.append(f"**Batch**: {c.batch_no}")
    if c.affected_quantity:
        filled.append(f"**Affected Qty**: {c.affected_quantity}")
    if c.manufacturing_date:
        filled.append(f"**Mfg Date**: {c.manufacturing_date}")
    if c.expiry_date:
        filled.append(f"**Expiry Date**: {c.expiry_date}")
    if c.complaint_category:
        filled.append(f"**Category**: {str(c.complaint_category).replace('_', ' ').title()}")
    if c.complaint_description and len(c.complaint_description) > 10:
        desc_preview = c.complaint_description[:120]
        if len(c.complaint_description) > 120:
            desc_preview += "..."
        filled.append(f"**Description**: {desc_preview}")

    sev_display = (sev or "major").upper()
    lines = [f"✅ **Complaint {num}** logged with severity [{sev_display}]."]

    if filled:
        lines.append("\n**Extracted from your message:**")
        lines.extend(f"• {f}" for f in filled)

    # AI Risk Assessment summary
    if next_action:
        lines.append(f"\n**Suggested Action**: {next_action}")
    if risk_assessment and risk_assessment not in {"Standard QA review.", ""}:
        lines.append(f"**Risk**: {risk_assessment[:200]}")

    # Missing fields
    missing = _get_missing_fields_prompt(c)
    lines.append(missing)

    return "\n".join(lines)


def _build_correction_reply(c: Complaint, diff: Dict[str, Any]) -> str:
    num = c.complaint_number
    missing_prompt = _get_missing_fields_prompt(c)
    if not diff:
        return f"I didn't detect any field changes in your message for complaint **{num}**.{missing_prompt}"

    # Show human-readable labels
    changes = []
    for k, v in diff.items():
        label = _FIELD_LABELS.get(k, k.replace("_", " ").title())
        changes.append(f"**{label}** → {v}")

    header = f"✏️ Updated {len(diff)} field(s) on **{num}**:"
    return header + "\n• " + "\n• ".join(changes) + "." + missing_prompt


def _parse_date_safe(val: Any):
    """Parse a date string in many natural formats into a Python date."""
    if not val or not isinstance(val, str):
        return None
    raw = val.strip()

    # Month abbreviation normalisation: "feb" → "02", "Feb" → same
    import re as _re
    _MONTH_MAP = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    def _norm(s: str) -> str:
        """Replace month abbreviations with zero-padded numbers."""
        def rep(m):
            return _MONTH_MAP.get(m.group(0).lower(), m.group(0))
        return _re.sub(r'(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', rep, s)

    normalised = _norm(raw)

    # Normalise separators: '/', '-', ' ' all become '-'
    normalised = _re.sub(r'[/\s]+', '-', normalised)

    _FMTS = [
        "%Y-%m-%d",   # 2025-02-25
        "%d-%m-%Y",   # 25-02-2025
        "%m-%Y",      # 02-2025  (month/year only → first of month)
        "%Y-%m",      # 2025-02  (year-month)
    ]
    for fmt in _FMTS:
        try:
            return datetime.strptime(normalised, fmt).date()
        except Exception:
            continue
    return None


def _is_conversational_query(text: str) -> bool:
    """
    Returns True if the message is a question, QA instruction, explanation request,
    summary request, or general assistance prompt (not a direct field assignment/correction).
    """
    import re as _re
    cleaned = (text or "").strip().lower()

    # ---- 1. Check for explicit field assignment / update commands first ----
    # If the user says "change batch to X", "batch is Y", "set product to Z", this is a field update.
    update_patterns = [
        r'\b(change|set|update|correct|make|edit|replace)\s+(the\s+)?(batch|lot|product|strength|quantity|qty|expiry|exp|mfg|category|severity|customer|site|contact)\s+(to|as|=)\s+',
        r'\b(batch|lot|customer|product|strength|quantity|qty|category|severity|site|block|npm)\s*(is|:|=)\s*[a-zA-Z0-9]',
        r'^\s*[a-zA-Z0-9_\-]+\s*(:|=>|=)\s*[a-zA-Z0-9]',  # key: value
    ]
    for pat in update_patterns:
        if _re.search(pat, cleaned, _re.IGNORECASE):
            return False

    # ---- 2. Explicit question, guidance, instruction, or explanation signals ----
    conversational_patterns = [
        "what", "which", "where", "who", "how", "why", "when",
        "what's", "whats", "what is", "which is", "where is",
        "suggest", "explain", "summarize", "summary", "tell me",
        "can you", "could you", "would you", "please tell", "please explain", "please suggest",
        "check", "is this", "are there", "do we have", "how to", "how do", "how should",
        "what fields", "which fields", "missing fields", "what's missing", "what is missing",
        "anything else", "is that all", "are we done",
        "looks good", "ok", "okay", "thanks", "thank you", "got it",
        "noted", "understood", "great", "perfect", "sure", "alright",
        "help me", "guide me", "advice", "recommend", "recommendation",
    ]
    if any(cleaned == p or cleaned.startswith(p + " ") or cleaned.startswith(p + "?") or f" {p} " in f" {cleaned} " for p in conversational_patterns):
        return True

    # If the text ends with a question mark, it's definitely a question
    if cleaned.endswith("?"):
        return True

    # Short message with no assignment
    field_keywords = {
        "batch", "lot", "tablet", "capsule", "vial", "mg", "ml", "quantity",
        "qty", "expiry", "exp", "manufacturing", "mfg", "strength", "product",
        "customer", "reporter", "source", "category", "description", "contact",
        "site", "block", "npm", "amox", "metop", "pharma", "pharmacy",
    }
    if len(cleaned) < 15 and not any(kw in cleaned for kw in field_keywords):
        return True

    return False



def _format_form_snapshot(complaint: Optional["Complaint"], current_form: Optional[Dict[str, Any]]) -> str:
    """Combines complaint model and live frontend form fields into a unified summary string."""
    fields = {}
    if complaint:
        fields = _complaint_to_dict(complaint)
    if current_form and isinstance(current_form, dict):
        for k, v in current_form.items():
            if v is not None and str(v).strip() != "":
                fields[k] = v

    if not fields:
        return "No fields filled yet."

    lines = []
    labels = [
        ("complaint_number", "Complaint #"),
        ("product_name", "Product"),
        ("product_strength", "Strength"),
        ("batch_no", "Batch #"),
        ("affected_quantity", "Quantity"),
        ("customer_name", "Customer / Reporter"),
        ("complainant_contact", "Contact"),
        ("manufacturing_date", "Mfg Date"),
        ("expiry_date", "Exp Date"),
        ("originating_site_block", "Site Block"),
        ("impacted_npm", "Material Code / NPM"),
        ("complaint_category", "Category"),
        ("severity", "Severity"),
        ("complaint_description", "Defect Description"),
        ("suggested_next_action", "Next Action"),
        ("initial_risk_assessment", "Risk Assessment"),
    ]
    for key, label in labels:
        val = fields.get(key)
        if val:
            lines.append(f"- {label}: {val}")

    return "\n".join(lines) if lines else "No fields filled yet."


async def _generate_conversational_reply(
    complaint: "Complaint",
    user_message: str,
    chat_history: list,
    current_form: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Calls Llama 3.3 to generate an intelligent, context-aware conversational reply
    for user queries, instructions, summaries, regulatory questions, and form checks.

    Includes current complaint state + live manual form edits + missing fields + chat history.
    """
    missing_prompt = _get_missing_fields_prompt(complaint)
    form_summary = _format_form_snapshot(complaint, current_form)

    history_text = ""
    if chat_history:
        lines = []
        for turn in chat_history[-8:]:
            role = "User" if turn.get("role") == "user" else "Assistant"
            lines.append(f"{role}: {turn.get('content', '')}")
        history_text = "\nConversation so far:\n" + "\n".join(lines) + "\n"

    system = (
        "You are CUSTOMER AI-Copilot, an expert Pharmaceutical Quality Management System (QMS) "
        "and QA Compliance Assistant. You have full, real-time visibility into the complaint intake form "
        "and any manual edits the user made on their screen.\n\n"
        "YOUR CAPABILITIES:\n"
        "1. Direct Form Context: If the user asks about the form (e.g. 'what is my batch?', 'what fields are missing?', 'check this form'), reference the live form values provided below.\n"
        "2. General QA & Regulatory Guidance: You can answer questions about GMP, ICH Q10, FDA 21 CFR 211.198, CAPA, root cause analysis, defect classifications (Critical vs Major vs Minor), adverse event reporting, and retention samples.\n"
        "3. Drafting & Analysis: You can summarize the complaint, rewrite descriptions into formal QA phrasing, suggest root causes, or recommend next actions.\n"
        "4. Tone: Helpful, knowledgeable, precise, and professional. Keep replies clear and concise (2-4 sentences unless detailed analysis is asked). Do NOT output JSON."
    )

    prompt = (
        f"LIVE FORM STATE & MANUAL EDITS:\n{form_summary}\n\n"
        f"MISSING FIELDS STATUS: {missing_prompt}\n"
        f"{history_text}"
        f"\nUSER REQUEST / MESSAGE: \"{user_message}\"\n\n"
        f"Provide a helpful, direct response to the user's request."
    )

    try:
        reply = await acall_llama(prompt=prompt, system=system, temperature=0.3, max_tokens=400)
        return reply.strip() or "I'm reviewing your complaint details. Let me know if you need to update any fields or submit to QMS."
    except Exception as exc:
        logger.warning("_generate_conversational_reply LLM error: %s", exc)
        base = f"I'm reviewing complaint {complaint.complaint_number}."
        return base + missing_prompt


def _is_greeting_message(text: str) -> bool:
    """
    Returns True for any message that is clearly conversational with no complaint data.
    Covers casual openers, questions about the system, short chit-chat, etc.
    """
    cleaned = (text or "").strip().lower()

    # Hard complaint signals — if present, this is NOT a greeting
    import re as _re
    complaint_signals = [
        r'\b(batch|lot)\s*(?:number|no|#)?\s*[:\-]?\s*[A-Z0-9]{3,}',
        r'\b(product|drug|medicine|tablet|capsule|vial|injection)\b',
        r'\b(defect|complaint|issue|problem|damaged|broken|contaminated|expired)\b',
        r'\b\d+\s*(mg|ml|tablets?|capsules?|vials?|bottles?|units?)\b',
    ]
    for pat in complaint_signals:
        if _re.search(pat, cleaned, _re.IGNORECASE):
            return False

    # Explicit greeting / intro words
    greeting_words = {
        "hi", "hello", "hey", "help", "test", "who are you", "what can you do",
        "good morning", "good afternoon", "good evening", "greetings", "hy", "hlo", "yo",
        "start", "begin", "hii", "hiii", "helo",
    }
    if cleaned in greeting_words:
        return True

    # Short message with no substance → treat as greeting/chit-chat
    if len(cleaned) < 12 and not any(kw in cleaned for kw in [
        "batch", "tablet", "capsule", "vial", "mg", "ml", "lot", "defect",
        "quality", "amox", "metop", "pharma", "product", "customer",
    ]):
        return True

    # Casual fill-form openers — no actual data, just intent expressions
    casual_openers = [
        "i want to", "i wanted to", "i need to", "i have to", "i would like to",
        "i'd like to", "i need help", "i want help", "help me", "can you help",
        "can i", "how do i", "how can i", "how to", "how do you",
        "let me", "let's", "lets", "shall we", "should i",
        "please help", "please assist", "please guide",
        "what should", "what do i", "where do i",
        "i'm here to", "i am here to", "im here to",
        "assist me", "guide me",
    ]
    if any(cleaned.startswith(p) or cleaned == p for p in casual_openers):
        return True

    return False


def _has_complaint_substance(text: str) -> bool:
    """
    Returns True only when the message appears to contain real complaint data
    that is worth running through the full intake pipeline.

    Requires at least TWO of the five complaint signals, OR one strong signal
    with sufficient text length (>40 chars), to avoid false-positives on
    vague short phrases.
    """
    import re as _re
    cleaned = (text or "").strip()

    if len(cleaned) < 20:
        return False

    signals = [
        # Batch / lot number
        bool(_re.search(r'\b(batch|lot)\s*(?:number|no|#|:)?\s*[A-Z0-9]{3,}', cleaned, _re.IGNORECASE)),
        # Product / drug name
        bool(_re.search(r'\b(amoxicillin|metoprolol|paracetamol|ibuprofen|aspirin|insulin|capsule|tablet|vial|injection|drug|medicine|product)\b', cleaned, _re.IGNORECASE)),
        # Physical defect description
        bool(_re.search(r'\b(defect|contaminated|broken|damaged|discolored|discolouration|melted|cracked|missing|wrong|incorrect|expired|leaking|foreign|particulate|crack|chip|dissolve)\b', cleaned, _re.IGNORECASE)),
        # Quantity + unit
        bool(_re.search(r'\b\d+\s*(mg|ml|mcg|iu|tablets?|capsules?|vials?|bottles?|strips?|packs?|units?)\b', cleaned, _re.IGNORECASE)),
        # Customer / reporter entity
        bool(_re.search(r'\b(pharmacy|hospital|clinic|patient|doctor|customer|reporter|dispensary)\b.*\b(complain|report|issue|problem|found|noticed|received)\b', cleaned, _re.IGNORECASE)),
        # Multi-line or long structured text (email / formal complaint)
        len(cleaned) > 120 and '\n' in cleaned,
    ]

    count = sum(signals)
    # Need 2+ signals, OR 1 signal with long enough text
    return count >= 2 or (count >= 1 and len(cleaned) > 60)


async def _generate_initial_reply(
    user_message: str,
    chat_history: list,
    current_form: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generates an intelligent, conversational reply for messages that don't
    yet trigger full complaint logging — casual openers, questions, QMS inquiries,
    or queries referring to manual form entries.
    """
    form_summary = _format_form_snapshot(None, current_form)

    system = (
        "You are CUSTOMER AI-Copilot, an intelligent Pharmaceutical Quality Management System (QMS) "
        "and QA Compliance Assistant. You help QA staff log customer complaints and answer quality compliance questions.\n\n"
        "CAPABILITIES:\n"
        "1. If the user asks about the form or has manually typed details on screen, acknowledge those fields using the Live Form State provided below.\n"
        "2. If the user asks general QA, GMP, CAPA, or regulatory questions, answer them accurately and professionally.\n"
        "3. If the user wants to log a new complaint, invite them to share the product name, batch number, customer, and issue description.\n"
        "4. Tone: Warm, professional, concise, and helpful (2-3 sentences). Plain text only, no JSON."
    )

    history_text = ""
    if chat_history:
        lines = []
        for turn in chat_history[-6:]:
            role = "User" if turn.get("role") == "user" else "Assistant"
            lines.append(f"{role}: {turn.get('content', '')}")
        history_text = "Conversation so far:\n" + "\n".join(lines) + "\n\n"

    prompt = (
        f"LIVE FORM STATE ON SCREEN:\n{form_summary}\n\n"
        f"{history_text}"
        f"USER MESSAGE: \"{user_message}\"\n\n"
        "Reply helpfully and concisely to the user."
    )

    try:
        reply = await acall_llama(prompt=prompt, system=system, temperature=0.3, max_tokens=300)
        return reply.strip() or (
            "Hello! I'm your AI Copilot for complaint intake. "
            "Please share the product name, batch number, and defect description — I'll extract everything and fill the form for you!"
        )
    except Exception as exc:
        logger.warning("_generate_initial_reply LLM error: %s", exc)
        return (
            "Hello! I'm here to help you log a quality complaint. "
            "Please share the product name, batch/lot number, and describe the defect — "
            "I'll extract all details and populate the form automatically."
        )


def _is_submit_intent(text: str) -> bool:
    """Returns True if the user wants to commit / submit the current complaint."""
    cleaned = (text or "").strip().lower()
    submit_phrases = {
        "submit", "commit", "save", "submit complaint", "commit complaint",
        "submit it", "commit it", "save it", "done", "submit now", "commit now",
        "commit to qms", "submit to qms", "go ahead", "proceed", "finalise", "finalize",
        "log it", "log complaint",
    }
    return cleaned in submit_phrases or any(cleaned.startswith(p) for p in submit_phrases)
