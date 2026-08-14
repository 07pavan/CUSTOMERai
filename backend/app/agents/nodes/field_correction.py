"""
app/agents/nodes/field_correction.py
---------------------------------------
LangGraph Node: Field Correction & Conversational Fill Agent

Handles two scenarios in one node:

  1. CORRECTION  — user explicitly corrects an existing field value
       "actually the batch is AMX240603, not AMX240602"
       → returns diff: {"batch_no": "AMX240603"}

  2. FILL-IN     — user answers the AI's question about a missing field
       AI asked: "Could you please tell me the Expiry Date?"
       User said: "2026/feb/2"
       → returns diff: {"expiry_date": "2026/feb/2"}

The LLM receives:
  - Current field values (so it knows what's already filled vs empty)
  - Full conversation history (so it understands what the AI was asking)
  - The user's latest message

It returns ONLY the fields that should change or be filled.
"""

import json
import logging
from typing import Any, Dict

from app.agents.llm import acall_gemma, acall_json, call_gemma, call_json
from app.agents.state import ComplaintState
from app.core.config import settings

logger = logging.getLogger(__name__)

# Allowed field names across all 6 sections of the Intake Form
ALLOWED_M1_FIELDS = {
    "complaint_source",
    "customer_name",
    "complainant_contact",
    "product_name",
    "product_strength",
    "batch_no",
    "affected_quantity",
    "manufacturing_date",
    "expiry_date",
    "originating_site_block",
    "impacted_npm",
    "complaint_category",
    "complaint_description",
    "severity",
    "suggested_next_action",
    "initial_risk_assessment",
}

FIELD_CORRECTION_SYSTEM_PROMPT = """
You are a Dynamic Field Extraction Specialist for a Pharmaceutical QMS complaint form.

Your role is DUAL — handle both dynamic corrections AND conversational fill-ins for ALL 16 fields across the intake form:

SCENARIO A — CORRECTION:
  The user explicitly corrects or updates an existing field value.
  Example: "actually the batch is AMX240603, quantity is 15 bottles" → {"batch_no": "AMX240603", "affected_quantity": "15 bottles"}
  Example: "change severity to critical and site to Packaging Line 2" → {"severity": "critical", "originating_site_block": "Packaging Line 2"}
  Example: "customer phone number is +1-555-0199" → {"complainant_contact": "+1-555-0199"}

SCENARIO B — FILL-IN (multi-turn conversation):
  The AI asked for missing fields or the user is providing new details:
  Example:
    History: Assistant: "Could you please provide the Expiry Date and NPM code?"
    User: "2027/12/31 and NPM-8821"
    → {"expiry_date": "2027/12/31", "impacted_npm": "NPM-8821"}

ALLOWED FIELD NAMES AND VALUE RULES:
- "complaint_source"       : one of 'pharmacy', 'email', 'portal', 'phone', 'paper'
- "customer_name"          : string — name of pharmacy, hospital, clinic, patient, or reporter
- "complainant_contact"    : string — phone number, email address, or contact details
- "product_name"           : string — brand or generic drug name
- "product_strength"       : string — e.g. '500mg', '10mg/mL', '5%'
- "batch_no"               : string — UPPERCASE, e.g. 'AMX240602'
- "affected_quantity"      : string — e.g. '48 capsules', '3 vials', '1500 tablets', '4 bottles'
- "manufacturing_date"     : string — e.g. '2025/2/25'
- "expiry_date"            : string — e.g. '2026/feb/2'
- "originating_site_block" : string — manufacturing block, plant, or facility site
- "impacted_npm"           : string — non-product material ID or packaging lot
- "complaint_category"     : one of 'quality', 'adverse_event', 'counterfeit', 'other'
- "complaint_description"  : string — defect details or clinical complaint description
- "severity"               : one of 'critical', 'major', 'minor'
- "suggested_next_action"  : string — immediate QA containment action
- "initial_risk_assessment": string — risk rationale or impact evaluation

STRICT OUTPUT RULES:
1. Return ONLY a valid JSON object with fields that should be CHANGED or FILLED.
2. Do NOT re-include unchanged fields.
3. Do NOT invent values — only extract what the user explicitly stated or confirmed.
4. If nothing should change, return {}.
"""

FIELD_CORRECTION_USER_TEMPLATE = """
CURRENT COMPLAINT FIELD VALUES:
{existing_fields_json}

{empty_fields_block}

{chat_history_block}

USER'S LATEST MESSAGE:
"{correction_message}"

Return the JSON diff of ONLY the fields that should be updated or filled:
"""


def _build_history_block(chat_history) -> str:
    """Formats the last N chat turns into a readable context block for the LLM."""
    if not chat_history:
        return ""
    lines = ["\nCONVERSATION HISTORY (most recent last, use this to understand what the AI asked):"]
    for turn in chat_history[-12:]:  # include up to 12 turns for full context
        role = "User" if turn.get("role") == "user" else "Assistant (AI Copilot)"
        content = str(turn.get("content") or "").strip()
        if content:
            lines.append(f"  {role}: {content}")
    lines.append("")
    return "\n".join(lines)


def _build_empty_fields_block(existing_fields: Dict[str, Any]) -> str:
    """Lists fields that are currently null/empty so the LLM knows what needs filling."""
    empty = []
    label_map = {
        "customer_name": "Customer/Reporter Name",
        "product_name": "Product Name",
        "product_strength": "Product Strength / Grade",
        "batch_no": "Batch / Lot Number",
        "affected_quantity": "Affected Quantity",
        "manufacturing_date": "Manufacturing Date",
        "expiry_date": "Expiry Date",
        "originating_site_block": "Originating Site Block",
        "impacted_npm": "Impacted Non-Product Materials",
        "complaint_description": "Complaint Description",
    }
    placeholder_values = {"unknown", "n/a", "none", "unspecified product", "anonymous reporter", ""}
    for field, label in label_map.items():
        val = existing_fields.get(field)
        if val is None or (isinstance(val, str) and val.strip().lower() in placeholder_values):
            empty.append(f"  - {label} ({field})")

    if not empty:
        return "\nCURRENTLY MISSING FIELDS: None — all fields are filled.\n"
    return "\nCURRENTLY MISSING / EMPTY FIELDS (prioritise filling these):\n" + "\n".join(empty) + "\n"


# ---------------------------------------------------------------------------
# Node Functions (Async & Sync)
# ---------------------------------------------------------------------------

async def field_correction_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: handles both field corrections AND conversational fill-ins.
    Uses full chat history for context so it can map answers to the right fields.
    """
    existing_fields = state.get("extracted_fields") or {}
    correction_message = (
        state.get("correction_message")
        or state.get("incoming_message")
        or state.get("raw_text")
        or ""
    ).strip()
    chat_history = state.get("chat_history") or []

    if not correction_message:
        return {"field_diff": {}, "extracted_fields": existing_fields}

    if not settings.GROQ_API_KEY:
        logger.info("GROQ_API_KEY unconfigured. Using heuristic field correction.")
        cleaned_diff = _heuristic_correction_diff(correction_message)
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        return {"field_diff": cleaned_diff, "extracted_fields": merged_fields}

    history_block = _build_history_block(chat_history)
    empty_fields_block = _build_empty_fields_block(existing_fields)
    user_prompt = FIELD_CORRECTION_USER_TEMPLATE.format(
        existing_fields_json=json.dumps(existing_fields, indent=2),
        empty_fields_block=empty_fields_block,
        chat_history_block=history_block,
        correction_message=correction_message,
    )

    try:
        raw_diff: Dict[str, Any] = await acall_json(
            async_llm_callable=acall_gemma,
            prompt=user_prompt,
            system=FIELD_CORRECTION_SYSTEM_PROMPT,
            max_retries=2,
        )

        cleaned_diff = _filter_and_clean_diff(raw_diff)
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)

        logger.info("field_correction_node completed: diff=%s", list(cleaned_diff.keys()))
        return {"field_diff": cleaned_diff, "extracted_fields": merged_fields}

    except Exception as exc:
        logger.warning("field_correction_node LLM error: %s. Using heuristic fallback.", exc)
        cleaned_diff = _heuristic_correction_diff(correction_message)
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        return {"field_diff": cleaned_diff, "extracted_fields": merged_fields}


def field_correction_node_sync(state: ComplaintState) -> ComplaintState:
    """Synchronous version of field_correction_node."""
    existing_fields = state.get("extracted_fields") or {}
    correction_message = (
        state.get("correction_message")
        or state.get("incoming_message")
        or state.get("raw_text")
        or ""
    ).strip()
    chat_history = state.get("chat_history") or []

    if not correction_message:
        return {"field_diff": {}, "extracted_fields": existing_fields}

    if not settings.GROQ_API_KEY:
        cleaned_diff = _heuristic_correction_diff(correction_message)
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        return {"field_diff": cleaned_diff, "extracted_fields": merged_fields}

    history_block = _build_history_block(chat_history)
    empty_fields_block = _build_empty_fields_block(existing_fields)
    user_prompt = FIELD_CORRECTION_USER_TEMPLATE.format(
        existing_fields_json=json.dumps(existing_fields, indent=2),
        empty_fields_block=empty_fields_block,
        chat_history_block=history_block,
        correction_message=correction_message,
    )

    try:
        raw_diff: Dict[str, Any] = call_json(
            llm_callable=call_gemma,
            prompt=user_prompt,
            system=FIELD_CORRECTION_SYSTEM_PROMPT,
            max_retries=2,
        )
        cleaned_diff = _filter_and_clean_diff(raw_diff)
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        return {"field_diff": cleaned_diff, "extracted_fields": merged_fields}

    except Exception as exc:
        logger.warning("field_correction_node_sync LLM error: %s. Using heuristic fallback.", exc)
        cleaned_diff = _heuristic_correction_diff(correction_message)
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        return {"field_diff": cleaned_diff, "extracted_fields": merged_fields}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_and_clean_diff(raw_diff: Dict[str, Any]) -> Dict[str, Any]:
    """Validates and cleans the raw LLM output diff for all 16 intake fields."""
    cleaned = {}
    alias_map = {
        "complainant_name": "customer_name",
        "reporter_name": "customer_name",
        "customer": "customer_name",
        "contact": "complainant_contact",
        "phone": "complainant_contact",
        "phone_number": "complainant_contact",
        "email": "complainant_contact",
        "contact_info": "complainant_contact",
        "source_type": "complaint_source",
        "source": "complaint_source",
        "category": "complaint_category",
        "description": "complaint_description",
        "defect_description": "complaint_description",
        "defect": "complaint_description",
        "strength": "product_strength",
        "dosage": "product_strength",
        "mfg_date": "manufacturing_date",
        "manufacture_date": "manufacturing_date",
        "exp_date": "expiry_date",
        "expiration_date": "expiry_date",
        "lot_no": "batch_no",
        "lot_number": "batch_no",
        "batch_number": "batch_no",
        "lot": "batch_no",
        "qty": "affected_quantity",
        "quantity": "affected_quantity",
        "site": "originating_site_block",
        "facility": "originating_site_block",
        "plant": "originating_site_block",
        "block": "originating_site_block",
        "npm": "impacted_npm",
        "npm_code": "impacted_npm",
        "non_product_material": "impacted_npm",
        "risk": "severity",
        "risk_level": "severity",
        "action": "suggested_next_action",
        "next_action": "suggested_next_action",
        "risk_assessment": "initial_risk_assessment",
        "risk_rationale": "initial_risk_assessment",
    }

    for k, v in raw_diff.items():
        target_k = alias_map.get(k, k)
        if target_k in ALLOWED_M1_FIELDS and v is not None:
            if target_k == "batch_no" and isinstance(v, str):
                cleaned[target_k] = v.strip().upper()
            elif target_k == "severity" and isinstance(v, str):
                s = v.strip().lower()
                cleaned[target_k] = s if s in {"critical", "major", "minor"} else "major"
            elif target_k in ("complaint_source",) and isinstance(v, str):
                src = v.strip().lower()
                cleaned[target_k] = src if src in {"pharmacy", "email", "portal", "phone", "paper"} else "email"
            elif target_k in ("complaint_category",) and isinstance(v, str):
                cat = v.strip().lower()
                cleaned[target_k] = cat if cat in {"quality", "adverse_event", "counterfeit", "other"} else "quality"
            else:
                cleaned[target_k] = v
    return cleaned


def _heuristic_correction_diff(msg: str) -> Dict[str, Any]:
    """Regex / keyword heuristic fallback when LLM is offline."""
    import re
    diff = {}

    batch_match = re.search(
        r'(?:batch|lot)(?:\s+number|\s+no|\s+#)?\s+(?:is\s+)?([A-Z0-9\-_]{4,25})',
        msg, re.IGNORECASE
    )
    if batch_match:
        diff["batch_no"] = batch_match.group(1).strip().upper()

    qty_match = re.search(
        r'(?:affected\s+quantity|quantity|qty)\s+(?:is\s+)?(\d+(?:\s*[a-zA-Z]+)?)',
        msg, re.IGNORECASE
    )
    if qty_match:
        diff["affected_quantity"] = qty_match.group(1).strip()

    name_match = re.search(
        r'(?:customer|customer\s+name|reporter|complainant)\s+(?:is\s+)?([A-Za-z\s]{3,40})',
        msg, re.IGNORECASE
    )
    if name_match:
        diff["customer_name"] = name_match.group(1).strip()

    prod_match = re.search(
        r'(?:product\s+name|product)\s+(?:is\s+)?([A-Za-z0-9\s]{3,30})',
        msg, re.IGNORECASE
    )
    if prod_match:
        diff["product_name"] = prod_match.group(1).strip()

    # Date patterns
    mfg_match = re.search(
        r'(?:manufacturing|mfg|manufacture|mfg\s*date|manufacturing\s*date|mfd)\s+(?:date\s+)?(?:is\s+)?([0-9A-Za-z/\-\.]+)',
        msg, re.IGNORECASE
    )
    if mfg_match:
        diff["manufacturing_date"] = mfg_match.group(1).strip()

    exp_match = re.search(
        r'(?:expiry|expiration|exp|exp\s*date|expiry\s*date|expires?)\s+(?:date\s+)?(?:is\s+)?([0-9A-Za-z/\-\.]+)',
        msg, re.IGNORECASE
    )
    if exp_match:
        diff["expiry_date"] = exp_match.group(1).strip()

    return diff


def _sync_aliases(fields: Dict[str, Any]) -> None:
    """Keeps backward-compat aliases in sync."""
    if "customer_name" in fields:
        fields["complainant_name"] = fields["customer_name"]
    if "complaint_source" in fields:
        fields["source_type"] = fields["complaint_source"]
    if "complaint_category" in fields:
        fields["category"] = fields["complaint_category"]
    if "complaint_description" in fields:
        fields["description"] = fields["complaint_description"]
