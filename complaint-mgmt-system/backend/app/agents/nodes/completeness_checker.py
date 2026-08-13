"""
app/agents/nodes/completeness_checker.py
-----------------------------------------
LangGraph Node: Completeness Checker

Evaluates the completeness of a complaint based on `state['extracted_fields']`.

Two-stage evaluation:
  1. Deterministic Rule Check:
     Checks for missing or null values in required fields:
     `product_name`, `batch_no`, `complainant_contact`, `description`.
     Also checks if `batch_no` is set to placeholder strings like 'UNKNOWN' or 'N/A'.

  2. Soft LLM Specificity Check (Gemma 2 9B IT):
     Evaluates whether the description text is sufficiently specific to initiate a QA
     investigation (vs vague/non-actionable statements like "the product was bad").

Output
------
Populates `state['completeness_flags']` as a list of dicts:
    [
        {"field": "batch_no", "issue": "Missing required field", "severity": "HIGH"},
        {"field": "description", "issue": "Vague description", "reason": "Lacks specific defect details"}
    ]
"""

import logging
from typing import Any, Dict, List, Optional

from app.agents.llm import acall_gemma, acall_json, call_gemma, call_json
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)

# Required fields for a complaint to be considered actionably complete
REQUIRED_FIELDS = ["product_name", "batch_no", "complainant_contact", "description"]

PLACEHOLDER_VALUES = {"unknown", "n/a", "na", "none", "unspecified", "not provided", "[none provided]"}


# ---------------------------------------------------------------------------
# LLM Specificity Prompt
# ---------------------------------------------------------------------------

SPECIFICATION_CHECK_SYSTEM_PROMPT = """
You are a Quality Assurance Triager evaluating customer complaint descriptions.
Determine if the provided complaint description is specific enough for a QA team to investigate, OR if it is too vague.

Specific Description Criteria:
- Describes a concrete defect (e.g. tablet chipped, color turned yellow, unsealed blister, dark specks in liquid, wrong capsule color).
- Mentions observed physical characteristics or specific events.

Vague Description Criteria:
- Very generic statements like "medicine didn't work", "bad product", "didn't feel right", "poor quality".
- Lacks any physical details, batch context, or specific observed defect.

Respond with a single JSON object:
{
  "is_specific": true or false,
  "reason": "Short 1-sentence explanation of why it is specific or vague."
}
"""

SPECIFICATION_CHECK_USER_TEMPLATE = """
Complaint Description to evaluate:
"{description}"
"""


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

async def completeness_checker_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: evaluates `state['extracted_fields']` and populates `state['completeness_flags']`.

    Parameters
    ----------
    state : ComplaintState

    Returns
    -------
    Updated ComplaintState with `completeness_flags` populated.
    """
    extracted = state.get("extracted_fields", {})
    flags: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------------
    # 1. Deterministic Rule Check
    # -----------------------------------------------------------------------
    for field in REQUIRED_FIELDS:
        val = extracted.get(field)

        if val is None or (isinstance(val, str) and not val.strip()):
            flags.append({
                "field": field,
                "issue": f"Missing required field: {field}",
                "severity": "HIGH" if field in ("batch_no", "product_name") else "MEDIUM",
            })
        elif isinstance(val, str) and val.strip().lower() in PLACEHOLDER_VALUES:
            flags.append({
                "field": field,
                "issue": f"Placeholder or missing value provided for {field} ('{val.strip()}')",
                "severity": "HIGH" if field in ("batch_no", "product_name") else "MEDIUM",
            })

    # Optional check for complainant_name
    complainant_name = extracted.get("complainant_name")
    if not complainant_name or (isinstance(complainant_name, str) and complainant_name.strip().lower() in PLACEHOLDER_VALUES):
        flags.append({
            "field": "complainant_name",
            "issue": "Complainant name is missing or anonymous",
            "severity": "LOW",
        })

    # -----------------------------------------------------------------------
    # 2. Soft LLM Specificity Check (with deterministic fallback heuristic)
    # -----------------------------------------------------------------------
    description = extracted.get("description")
    if description and isinstance(description, str) and len(description.strip()) >= 3:
        desc_lower = description.strip().lower()
        vague_phrases = ["didn't work", "did not work", "felt bad", "bad product", "poor quality", "didn't feel right", "doesn't work"]

        llm_succeeded = False
        try:
            user_prompt = SPECIFICATION_CHECK_USER_TEMPLATE.format(description=description.strip())
            spec_result: Dict[str, Any] = await acall_json(
                async_llm_callable=acall_gemma,
                prompt=user_prompt,
                system=SPECIFICATION_CHECK_SYSTEM_PROMPT,
                max_retries=1,
            )

            llm_succeeded = True
            if not spec_result.get("is_specific", True):
                flags.append({
                    "field": "description",
                    "issue": "Description is too vague for QA investigation",
                    "reason": spec_result.get("reason", "Lacks specific physical defect details"),
                    "severity": "MEDIUM",
                })
        except Exception as exc:
            logger.warning("Soft LLM specificity check error (using fallback heuristic): %s", exc)

        # Fallback heuristic if LLM is offline / keyless
        if not llm_succeeded:
            if any(phrase in desc_lower for phrase in vague_phrases) or len(desc_lower) < 25:
                flags.append({
                    "field": "description",
                    "issue": "Description is too vague for QA investigation",
                    "reason": "Description lacks detailed physical observations or specific defect details.",
                    "severity": "MEDIUM",
                })

    logger.info(
        "completeness_checker_node completed: %d flags generated.", len(flags)
    )

    state["completeness_flags"] = flags
    return state


def completeness_checker_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of completeness_checker_node for standalone testing.
    """
    extracted = state.get("extracted_fields", {})
    flags: List[Dict[str, Any]] = []

    # 1. Deterministic Rule Check
    for field in REQUIRED_FIELDS:
        val = extracted.get(field)

        if val is None or (isinstance(val, str) and not val.strip()):
            flags.append({
                "field": field,
                "issue": f"Missing required field: {field}",
                "severity": "HIGH" if field in ("batch_no", "product_name") else "MEDIUM",
            })
        elif isinstance(val, str) and val.strip().lower() in PLACEHOLDER_VALUES:
            flags.append({
                "field": field,
                "issue": f"Placeholder or missing value provided for {field} ('{val.strip()}')",
                "severity": "HIGH" if field in ("batch_no", "product_name") else "MEDIUM",
            })

    complainant_name = extracted.get("complainant_name")
    if not complainant_name or (isinstance(complainant_name, str) and complainant_name.strip().lower() in PLACEHOLDER_VALUES):
        flags.append({
            "field": "complainant_name",
            "issue": "Complainant name is missing or anonymous",
            "severity": "LOW",
        })

    # 2. Soft LLM Specificity Check (with deterministic fallback heuristic)
    description = extracted.get("description")
    if description and isinstance(description, str) and len(description.strip()) >= 3:
        desc_lower = description.strip().lower()
        vague_phrases = ["didn't work", "did not work", "felt bad", "bad product", "poor quality", "didn't feel right", "doesn't work"]

        llm_succeeded = False
        try:
            user_prompt = SPECIFICATION_CHECK_USER_TEMPLATE.format(description=description.strip())
            spec_result: Dict[str, Any] = call_json(
                llm_callable=call_gemma,
                prompt=user_prompt,
                system=SPECIFICATION_CHECK_SYSTEM_PROMPT,
                max_retries=1,
            )

            llm_succeeded = True
            if not spec_result.get("is_specific", True):
                flags.append({
                    "field": "description",
                    "issue": "Description is too vague for QA investigation",
                    "reason": spec_result.get("reason", "Lacks specific physical defect details"),
                    "severity": "MEDIUM",
                })
        except Exception as exc:
            logger.warning("Soft LLM specificity check error (using fallback heuristic): %s", exc)

        # Fallback heuristic if LLM is offline / keyless
        if not llm_succeeded:
            if any(phrase in desc_lower for phrase in vague_phrases) or len(desc_lower) < 25:
                flags.append({
                    "field": "description",
                    "issue": "Description is too vague for QA investigation",
                    "reason": "Description lacks detailed physical observations or specific defect details.",
                    "severity": "MEDIUM",
                })

    state["completeness_flags"] = flags
    return state
