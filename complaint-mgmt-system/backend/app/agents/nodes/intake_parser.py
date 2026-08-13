"""
app/agents/nodes/intake_parser.py
----------------------------------
LangGraph Node: Intake Parser

Parses unstructured raw text (from emails, uploaded documents, or call transcripts)
into a structured JSON dictionary using Gemma 2 9B IT (`gemma2-9b-it`).

Fields extracted:
  - product_name       : Trade or generic name of the drug/device (str or null)
  - batch_no           : Lot / batch / control number (str or null)
  - complainant_name   : Name of reporting individual or entity (str or null)
  - complainant_contact: Email, phone, or address of reporter (str or null)
  - category           : One of 'quality' | 'adverse_event' | 'counterfeit' | 'other' (str or null)
  - description        : Concise summary of the reported issue (str or null)

Strict Instructions:
  - If a field is not explicitly present or determinable from the text, set it to null.
  - NEVER hallucinate or guess missing values.
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
You are a expert Pharmaceutical Quality Assurance (QA) intake specialist.
Your job is to read raw, unstructured complaint documents (emails, lab reports, call transcripts, packaging notes) and extract structured fields with 100% precision.

FIELD SPECIFICATION:
1. "product_name": (string or null) The brand or generic drug/product name.
2. "batch_no": (string or null) The lot, batch, or control number (e.g., "B2024-089A", "LOT-99321-X"). Set to null if missing or explicitly stated as unknown.
3. "complainant_name": (string or null) Full name of the reporter, doctor, patient, or facility. Set to null if anonymous or missing.
4. "complainant_contact": (string or null) Email address, phone number, or office address of the complainant. Set to null if missing.
5. "category": (string) Must be EXACTLY one of:
   - "quality"         : Physical defects, tablet chips, seal voids, contamination, discoloration, packaging flaws.
   - "adverse_event"   : Unexpected patient side effects, reactions, toxicity, hospitalization.
   - "counterfeit"     : Suspected fake packaging, bad hologram, unauthorized distributor, suspicious printing.
   - "other"           : General inquiries, administrative issues not matching above.
6. "description": (string) A clear, objective 1-3 sentence summary of the defect or complaint based ONLY on the text.

STRICT HALLUCINATION GUARD:
- If a field is NOT mentioned in the text, you MUST return null for that key.
- Do NOT make up batch numbers, phone numbers, or names.
"""

INTAKE_PARSER_USER_PROMPT_TEMPLATE = """
Extract structured fields from the following complaint document text:

--- BEGIN COMPLAINT TEXT ---
{raw_text}
--- END COMPLAINT TEXT ---

Respond with a single JSON object containing keys:
"product_name", "batch_no", "complainant_name", "complainant_contact", "category", "description".
"""


# ---------------------------------------------------------------------------
# Node Functions (Async & Sync versions)
# ---------------------------------------------------------------------------

async def intake_parser_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: parse `state['raw_text']` into `state['extracted_fields']`.

    Parameters
    ----------
    state : ComplaintState containing `raw_text`

    Returns
    -------
    Updated ComplaintState dictionary with `extracted_fields` populated.
    """
    raw_text = state.get("raw_text", "").strip()

    if not raw_text:
        logger.warning("intake_parser_node: raw_text is empty.")
        state["extracted_fields"] = {
            "product_name": None,
            "batch_no": None,
            "complainant_name": None,
            "complainant_contact": None,
            "category": "other",
            "description": "Empty complaint text received.",
        }
        return state

    user_prompt = INTAKE_PARSER_USER_PROMPT_TEMPLATE.format(raw_text=raw_text)

    try:
        extracted: Dict[str, Any] = await acall_json(
            async_llm_callable=acall_gemma,
            prompt=user_prompt,
            system=INTAKE_PARSER_SYSTEM_PROMPT,
            max_retries=2,
        )

        # Normalise / clean output structure
        cleaned_fields = {
            "product_name": extracted.get("product_name"),
            "batch_no": extracted.get("batch_no"),
            "complainant_name": extracted.get("complainant_name"),
            "complainant_contact": extracted.get("complainant_contact"),
            "category": _normalise_category(extracted.get("category")),
            "description": extracted.get("description", raw_text[:250]),
        }

        logger.info(
            "intake_parser_node completed: product='%s', batch='%s', category='%s'",
            cleaned_fields["product_name"],
            cleaned_fields["batch_no"],
            cleaned_fields["category"],
        )

        state["extracted_fields"] = cleaned_fields
        return state

    except Exception as exc:
        logger.error("intake_parser_node error: %s", exc)
        state["extracted_fields"] = {
            "product_name": None,
            "batch_no": None,
            "complainant_name": None,
            "complainant_contact": None,
            "category": "other",
            "description": raw_text[:250],
        }
        state["error"] = f"intake_parser_node failed: {exc}"
        return state


def intake_parser_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of intake_parser_node for non-async testing/pipelines.
    """
    raw_text = state.get("raw_text", "").strip()

    if not raw_text:
        state["extracted_fields"] = {
            "product_name": None,
            "batch_no": None,
            "complainant_name": None,
            "complainant_contact": None,
            "category": "other",
            "description": "Empty complaint text received.",
        }
        return state

    user_prompt = INTAKE_PARSER_USER_PROMPT_TEMPLATE.format(raw_text=raw_text)

    try:
        extracted: Dict[str, Any] = call_json(
            llm_callable=call_gemma,
            prompt=user_prompt,
            system=INTAKE_PARSER_SYSTEM_PROMPT,
            max_retries=2,
        )

        cleaned_fields = {
            "product_name": extracted.get("product_name"),
            "batch_no": extracted.get("batch_no"),
            "complainant_name": extracted.get("complainant_name"),
            "complainant_contact": extracted.get("complainant_contact"),
            "category": _normalise_category(extracted.get("category")),
            "description": extracted.get("description", raw_text[:250]),
        }

        state["extracted_fields"] = cleaned_fields
        return state

    except Exception as exc:
        logger.error("intake_parser_node_sync error: %s", exc)
        state["extracted_fields"] = {
            "product_name": None,
            "batch_no": None,
            "complainant_name": None,
            "complainant_contact": None,
            "category": "other",
            "description": raw_text[:250],
        }
        state["error"] = f"intake_parser_node_sync failed: {exc}"
        return state


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _normalise_category(val: Any) -> str:
    """Ensure category is one of the valid enum strings."""
    valid = {"quality", "adverse_event", "counterfeit", "other"}
    if isinstance(val, str) and val.lower().strip() in valid:
        return val.lower().strip()
    return "quality"  # Default fallback if LLM returns unexpected variation
