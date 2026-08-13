"""
app/agents/nodes/field_correction.py
---------------------------------------
LangGraph Node: Field Correction Agent

Parses user correction messages against an existing field dictionary using Gemma 2 9B IT.

Inputs:
  - state["extracted_fields"]   : Dict of currently extracted complaint fields
  - state["correction_message"] : User's correction/update message string

Output:
  - state["field_diff"]         : JSON dictionary containing ONLY the key-value pairs that changed
  - state["extracted_fields"]   : Merged dictionary updating extracted_fields with field_diff
"""

import json
import logging
from typing import Any, Dict

from app.agents.llm import acall_gemma, acall_json, call_gemma, call_json
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)

# Allowed M1 field names
ALLOWED_M1_FIELDS = {
    "complaint_source",
    "customer_name",
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
}

FIELD_CORRECTION_SYSTEM_PROMPT = """
You are a Precision Data Quality Specialist for a Pharmaceutical QMS system.
Your job is to read an existing set of extracted complaint fields alongside a user correction message, and extract ONLY the field corrections requested.

ALLOWED M1 FIELD NAMES:
- "complaint_source"       : ('pharmacy', 'email', 'portal', 'phone', 'paper')
- "customer_name"          : (string)
- "product_name"           : (string)
- "product_strength"       : (string)
- "batch_no"               : (string)
- "affected_quantity"      : (string)
- "manufacturing_date"     : (string)
- "expiry_date"            : (string)
- "originating_site_block" : (string)
- "impacted_npm"           : (string)
- "complaint_category"     : ('quality', 'adverse_event', 'counterfeit', 'other')
- "complaint_description"  : (string)

STRICT DIFF RULES:
1. Return ONLY a JSON dictionary of the fields that the user EXPLICITLY intended to change or update in their message.
2. Do NOT include or alter any fields that were NOT mentioned in the correction message.
3. Use the exact allowed M1 field names listed above.
4. If no fields were modified, return an empty JSON object `{}`.
"""

FIELD_CORRECTION_USER_TEMPLATE = """
CURRENT EXTRACTED FIELDS:
{existing_fields_json}

USER CORRECTION MESSAGE:
"{correction_message}"

Extract ONLY the JSON diff of changed fields:
"""


# ---------------------------------------------------------------------------
# Node Functions (Async & Sync)
# ---------------------------------------------------------------------------

async def field_correction_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: parses `correction_message` against `extracted_fields` and produces `field_diff`.
    """
    existing_fields = state.get("extracted_fields") or {}
    correction_message = (state.get("correction_message") or state.get("incoming_message") or state.get("raw_text") or "").strip()

    if not correction_message:
        state["field_diff"] = {}
        return state

    user_prompt = FIELD_CORRECTION_USER_TEMPLATE.format(
        existing_fields_json=json.dumps(existing_fields, indent=2),
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
        state["field_diff"] = cleaned_diff

        # Merge diff into extracted_fields
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        state["extracted_fields"] = merged_fields

        logger.info("field_correction_node completed: diff=%s", list(cleaned_diff.keys()))
        return state

    except Exception as exc:
        logger.warning("field_correction_node LLM error: %s. Using heuristic regex fallback.", exc)
        cleaned_diff = _heuristic_correction_diff(correction_message)
        state["field_diff"] = cleaned_diff
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        state["extracted_fields"] = merged_fields
        return state


def field_correction_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of field_correction_node for non-async scripts.
    """
    existing_fields = state.get("extracted_fields") or {}
    correction_message = (state.get("correction_message") or state.get("incoming_message") or state.get("raw_text") or "").strip()

    if not correction_message:
        state["field_diff"] = {}
        return state

    user_prompt = FIELD_CORRECTION_USER_TEMPLATE.format(
        existing_fields_json=json.dumps(existing_fields, indent=2),
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
        state["field_diff"] = cleaned_diff
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        state["extracted_fields"] = merged_fields
        return state

    except Exception as exc:
        logger.warning("field_correction_node_sync LLM error: %s. Using heuristic fallback.", exc)
        cleaned_diff = _heuristic_correction_diff(correction_message)
        state["field_diff"] = cleaned_diff
        merged_fields = {**existing_fields, **cleaned_diff}
        _sync_aliases(merged_fields)
        state["extracted_fields"] = merged_fields
        return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_and_clean_diff(raw_diff: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    alias_map = {
        "complainant_name": "customer_name",
        "source_type": "complaint_source",
        "category": "complaint_category",
        "description": "complaint_description",
    }

    for k, v in raw_diff.items():
        target_k = alias_map.get(k, k)
        if target_k in ALLOWED_M1_FIELDS and v is not None:
            if target_k == "batch_no" and isinstance(v, str):
                cleaned[target_k] = v.strip().upper()
            else:
                cleaned[target_k] = v
    return cleaned


def _heuristic_correction_diff(msg: str) -> Dict[str, Any]:
    """Regex / keyword heuristic fallback when LLM is offline."""
    import re
    diff = {}

    # Check for batch number pattern
    batch_match = re.search(r'(?:batch|lot)(?:\s+number|\s+no|\s+#)?\s+(?:is\s+)?([A-Z0-9\-_]{4,20})', msg, re.IGNORECASE)
    if batch_match:
        diff["batch_no"] = batch_match.group(1).upper()

    # Check for affected quantity pattern
    qty_match = re.search(r'(?:affected\s+quantity|quantity|qty)\s+(?:is\s+)?(\d+\s*[a-z]+)', msg, re.IGNORECASE)
    if qty_match:
        diff["affected_quantity"] = qty_match.group(1).strip()

    return diff


def _sync_aliases(fields: Dict[str, Any]) -> None:
    if "customer_name" in fields:
        fields["complainant_name"] = fields["customer_name"]
    if "complaint_source" in fields:
        fields["source_type"] = fields["complaint_source"]
    if "complaint_category" in fields:
        fields["category"] = fields["complaint_category"]
    if "complaint_description" in fields:
        fields["description"] = fields["complaint_description"]
