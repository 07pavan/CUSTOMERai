"""
app/agents/nodes/intake_parser.py
----------------------------------
LangGraph Node: Intake Parser

Parses unstructured raw text into structured JSON fields matching Prompt M1:
  - complaint_source      : One of 'pharmacy' | 'email' | 'portal' | 'phone' | 'paper'
  - customer_name         : Name of reporter, doctor, patient, facility, or pharmacy
  - product_name          : Brand or generic name of drug/device
  - product_strength      : Strength / concentration / grade (e.g., '500mg', '10mg/mL')
  - batch_no              : Lot / batch / control number
  - affected_quantity     : Quantity of affected product (e.g., '1500 tablets', '3 vials')
  - manufacturing_date    : Manufacturing date if present (YYYY-MM-DD or MM/YYYY)
  - expiry_date           : Expiration date if present (YYYY-MM-DD or MM/YYYY)
  - originating_site_block: Manufacturing block or site ID if mentioned
  - impacted_npm          : Non-product material ID or packaging code
  - complaint_category    : One of 'quality' | 'adverse_event' | 'counterfeit' | 'other'
  - complaint_description : Clear verbatim description of defect/complaint
"""

import logging
from typing import Any, Dict

from app.agents.llm import acall_gemma, acall_json, call_gemma, call_json
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

INTAKE_PARSER_SYSTEM_PROMPT = """
You are an expert Pharmaceutical Quality Assurance (QA) intake specialist.
Your job is to read raw complaint documents (emails, lab notices, transcripts) and extract structured fields with 100% precision.

FIELD SPECIFICATIONS:
1. "complaint_source": (string) One of: "pharmacy", "email", "portal", "phone", "paper".
2. "customer_name": (string or null) Full name of reporter, pharmacy, hospital, doctor, or facility.
3. "product_name": (string or null) Brand or generic drug name.
4. "product_strength": (string or null) Product strength, concentration, or dosage grade (e.g., "500mg", "10mg/mL").
5. "batch_no": (string or null) Batch, lot, or control number. Set to null if unknown/missing.
6. "affected_quantity": (string or null) Number of affected units (e.g., "1500 tablets", "48 bottles").
7. "manufacturing_date": (string or null) Manufacturing date if mentioned (e.g., "2025-01-15", "01/2025").
8. "expiry_date": (string or null) Expiration date if mentioned (e.g., "2026-11-30", "11/2026").
9. "originating_site_block": (string or null) Site block or facility section if mentioned (e.g., "Block B-4").
10. "impacted_npm": (string or null) Impacted Non-Product Material / packaging ID if mentioned (e.g., "NPM-9901").
11. "complaint_category": (string) Must be EXACTLY one of: "quality", "adverse_event", "counterfeit", "other".
12. "complaint_description": (string) Objective 1-3 sentence description of the defect/complaint based strictly on the text.

STRICT HALLUCINATION GUARD:
- If a field is not explicitly present in the text, return null for that key.
- Never invent batch numbers, names, or dates.
"""

INTAKE_PARSER_USER_PROMPT_TEMPLATE = """
Extract structured fields from the following complaint document text:

--- BEGIN COMPLAINT TEXT ---
{raw_text}
--- END COMPLAINT TEXT ---

Respond with a single JSON object containing keys:
"complaint_source", "customer_name", "product_name", "product_strength", "batch_no",
"affected_quantity", "manufacturing_date", "expiry_date", "originating_site_block",
"impacted_npm", "complaint_category", "complaint_description".
"""


# ---------------------------------------------------------------------------
# Node Functions (Async & Sync versions)
# ---------------------------------------------------------------------------

async def intake_parser_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: parse `state['raw_text']` into `state['extracted_fields']`.
    """
    raw_text = state.get("raw_text", "").strip()

    if not raw_text:
        logger.warning("intake_parser_node: raw_text is empty.")
        state["extracted_fields"] = _empty_extracted_fields("Empty complaint text received.")
        return state

    user_prompt = INTAKE_PARSER_USER_PROMPT_TEMPLATE.format(raw_text=raw_text)

    try:
        extracted: Dict[str, Any] = await acall_json(
            async_llm_callable=acall_gemma,
            prompt=user_prompt,
            system=INTAKE_PARSER_SYSTEM_PROMPT,
            max_retries=2,
        )

        cleaned_fields = _build_cleaned_fields(extracted, raw_text)
        logger.info(
            "intake_parser_node completed: product='%s', batch='%s', category='%s'",
            cleaned_fields.get("product_name"),
            cleaned_fields.get("batch_no"),
            cleaned_fields.get("complaint_category"),
        )
        state["extracted_fields"] = cleaned_fields
        return state

    except Exception as exc:
        logger.error("intake_parser_node error: %s", exc)
        state["extracted_fields"] = _empty_extracted_fields(raw_text[:250])
        state["error"] = f"intake_parser_node failed: {exc}"
        return state


def intake_parser_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of intake_parser_node for testing/pipelines.
    """
    raw_text = state.get("raw_text", "").strip()

    if not raw_text:
        state["extracted_fields"] = _empty_extracted_fields("Empty complaint text received.")
        return state

    user_prompt = INTAKE_PARSER_USER_PROMPT_TEMPLATE.format(raw_text=raw_text)

    try:
        extracted: Dict[str, Any] = call_json(
            llm_callable=call_gemma,
            prompt=user_prompt,
            system=INTAKE_PARSER_SYSTEM_PROMPT,
            max_retries=2,
        )
        state["extracted_fields"] = _build_cleaned_fields(extracted, raw_text)
        return state
    except Exception as exc:
        logger.error("intake_parser_node_sync error: %s", exc)
        state["extracted_fields"] = _empty_extracted_fields(raw_text[:250])
        state["error"] = f"intake_parser_node_sync failed: {exc}"
        return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_cleaned_fields(extracted: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    comp_source = extracted.get("complaint_source") or extracted.get("source_type") or "email"
    cust_name = extracted.get("customer_name") or extracted.get("complainant_name")
    cat = _normalise_category(extracted.get("complaint_category") or extracted.get("category"))
    desc = extracted.get("complaint_description") or extracted.get("description") or raw_text[:250]

    fields = {
        "complaint_source": comp_source,
        "customer_name": cust_name,
        "complainant_contact": extracted.get("complainant_contact"),
        "product_name": extracted.get("product_name"),
        "product_strength": extracted.get("product_strength"),
        "batch_no": extracted.get("batch_no"),
        "affected_quantity": extracted.get("affected_quantity"),
        "manufacturing_date": extracted.get("manufacturing_date"),
        "expiry_date": extracted.get("expiry_date"),
        "originating_site_block": extracted.get("originating_site_block"),
        "impacted_npm": extracted.get("impacted_npm"),
        "complaint_category": cat,
        "complaint_description": desc,

        # Backward-compatibility aliases
        "source_type": comp_source,
        "complainant_name": cust_name,
        "category": cat,
        "description": desc,
    }
    return fields


def _empty_extracted_fields(desc_text: str) -> Dict[str, Any]:
    return {
        "complaint_source": "email",
        "customer_name": None,
        "complainant_contact": None,
        "product_name": None,
        "product_strength": None,
        "batch_no": None,
        "affected_quantity": None,
        "manufacturing_date": None,
        "expiry_date": None,
        "originating_site_block": None,
        "impacted_npm": None,
        "complaint_category": "other",
        "complaint_description": desc_text,
        "source_type": "email",
        "complainant_name": None,
        "category": "other",
        "description": desc_text,
    }


def _normalise_category(val: Any) -> str:
    valid = {"quality", "adverse_event", "counterfeit", "other"}
    if isinstance(val, str) and val.lower().strip() in valid:
        return val.lower().strip()
    return "quality"
