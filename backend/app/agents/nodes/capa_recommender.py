"""
app/agents/nodes/capa_recommender.py
------------------------------------
LangGraph Node: CAPA Recommender

Formulates a draft Corrective and Preventive Action (CAPA) plan based on the
hypothesized root causes (`state['root_cause_suggestion']`), complaint category,
and risk level.

Structure:
  1. Corrective Action (Immediate Fix): Immediate containment actions (e.g. quarantine,
     RMA, retain sample testing, batch record review).
  2. Preventive Action (Systemic Fix): Long-term systemic improvements (e.g. SOP update,
     equipment re-calibration, supplier audit, process validation).

Regulatory Framing (21 CFR Part 211 / GXP):
Output MUST be explicitly framed as a starting-point draft for QA reviewer evaluation,
NOT a final decision.

Output:
  - state["capa_suggestion"] : Formatted text with Corrective & Preventive actions.
"""

import logging
from typing import Any, Dict, Optional

from app.agents.llm import acall_json, acall_llama, call_json, call_llama
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

CAPA_SYSTEM_PROMPT = """
You are a Pharmaceutical Quality Assurance Director specializing in CAPA (Corrective and Preventive Action) design.
Your task is to propose a draft CAPA plan based on the complaint details and hypothesized root cause.

DRAFT CAPA STRUCTURE:
1. "corrective_action": (Short paragraph / 2-3 bullet points) Immediate containment actions to control the immediate risk (e.g., quarantine affected lot, inspect retain samples, issue customer replacement / RMA, perform immediate batch record review).
2. "preventive_action": (Short paragraph / 2-3 bullet points) Long-term systemic fixes to prevent recurrence (e.g., update manufacturing SOP, re-calibrate equipment, perform supplier quality audit, revise in-process IPC testing).

REGULATORY FRAMING:
State explicitly that this is a DRAFT PROPOSAL intended as a starting point for QA review, NOT a finalized management decision.

JSON RESPONSE FORMAT:
Respond ONLY with a single JSON object:
{
  "corrective_action": "Immediate containment steps...",
  "preventive_action": "Systemic long-term preventive steps...",
  "framing_note": "Draft CAPA recommendation for QA Reviewer evaluation. Pending formal CAPA committee approval."
}
"""

CAPA_USER_TEMPLATE = """
Propose a draft CAPA plan for the following complaint:

Product Name: {product_name}
Batch Number: {batch_no}
Risk Level: {risk_level}
Hypothesized Root Cause:
{root_cause_suggestion}

Complaint Summary / Description:
{description}
"""


# ---------------------------------------------------------------------------
# Fallback Heuristic (Offline / Keyless Mode)
# ---------------------------------------------------------------------------

def _heuristic_capa(extracted: Dict[str, Any], root_cause: str, risk_level: str) -> str:
    """Fallback CAPA recommendation when LLM is unavailable."""
    batch = extracted.get("batch_no") or "unspecified lot"
    product = extracted.get("product_name") or "product"
    desc = (extracted.get("description") or "").lower()

    if "counterfeit" in desc or "hologram" in desc:
        corr = f"1. Immediately quarantine remaining stock of Lot {batch}.\n2. Issue Security Alert to distributor network and initiate forensic packaging analysis.\n3. File formal alert with Regulatory Authorities (FDA/EMA)."
        prev = "1. Revise secondary packaging authentication protocol to include serialized 2D matrix verification.\n2. Conduct mandatory Quality Audit of distributor network."
    elif "particulate" in desc or "vial" in desc:
        corr = f"1. Place quarantine hold on Lot {batch} across all distribution centers.\n2. Pull and inspect 100% of retain samples under polarized light.\n3. Conduct immediate batch production & cleanroom log review."
        prev = "1. Update cleanroom HVAC HEPA maintenance & particulate monitoring SOP.\n2. Re-validate elastomeric stopper siliconization and washing procedures."
    elif "chipped" in desc or "broken" in desc:
        corr = f"1. Issue replacement product to complainant.\n2. Quarantine lot {batch} retain samples and test friability per USP <1216>."
        prev = "1. Recalibrate tablet press compression tooling and automatic reject parameters.\n2. Revise IPC friability sampling frequency from 2-hour to 1-hour intervals."
    else:
        corr = f"1. Log complaint into QMS and place Lot {batch} on QA observation hold.\n2. Test retain samples for product {product}."
        prev = "1. Conduct trend analysis across recent manufacturing lots.\n2. Update relevant equipment operation SOP if trend exceeds baseline."

    return (
        f"[DRAFT CAPA RECOMMENDATION — FOR QA REVIEWER EVALUATION]\n\n"
        f"1. CORRECTIVE ACTION (Immediate Containment):\n{corr}\n\n"
        f"2. PREVENTIVE ACTION (Systemic Long-Term Fix):\n{prev}\n\n"
        f"Disclaimer: Starting-point proposal for QA investigation. Formal CAPA approval required prior to execution."
    )


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

async def capa_recommender_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: populates `state['capa_suggestion']`.
    """
    extracted = state.get("extracted_fields", {})
    root_cause = state.get("root_cause_suggestion", "")
    risk_level = (state.get("risk_level") or "major").upper()

    product_name = extracted.get("product_name") or "Pharmaceutical Product"
    batch_no = extracted.get("batch_no") or "Unspecified"
    description = extracted.get("description") or state.get("raw_text", "")[:400]

    user_prompt = CAPA_USER_TEMPLATE.format(
        product_name=product_name,
        batch_no=batch_no,
        risk_level=risk_level,
        root_cause_suggestion=root_cause,
        description=description,
    )

    try:
        res: Dict[str, Any] = await acall_json(
            async_llm_callable=acall_llama,
            prompt=user_prompt,
            system=CAPA_SYSTEM_PROMPT,
            max_retries=1,
        )

        corr = res.get("corrective_action", "")
        prev = res.get("preventive_action", "")
        framing = res.get("framing_note", "Draft CAPA recommendation for QA Reviewer evaluation.")

        if not corr or not prev:
            formatted_capa = _heuristic_capa(extracted, root_cause, risk_level)
        else:
            formatted_capa = (
                f"[DRAFT CAPA RECOMMENDATION — FOR QA REVIEWER EVALUATION]\n\n"
                f"1. CORRECTIVE ACTION (Immediate Containment):\n{corr}\n\n"
                f"2. PREVENTIVE ACTION (Systemic Long-Term Fix):\n{prev}\n\n"
                f"Disclaimer: {framing}"
            )

        state["capa_suggestion"] = formatted_capa
        logger.info("capa_recommender_node completed successfully.")
        return state

    except Exception as exc:
        logger.warning("capa_recommender_node LLM error: %s. Using heuristic fallback.", exc)
        state["capa_suggestion"] = _heuristic_capa(extracted, root_cause, risk_level)
        return state


def capa_recommender_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of capa_recommender_node for standalone testing.
    """
    extracted = state.get("extracted_fields", {})
    root_cause = state.get("root_cause_suggestion", "")
    risk_level = (state.get("risk_level") or "major").upper()

    product_name = extracted.get("product_name") or "Pharmaceutical Product"
    batch_no = extracted.get("batch_no") or "Unspecified"
    description = extracted.get("description") or state.get("raw_text", "")[:400]

    user_prompt = CAPA_USER_TEMPLATE.format(
        product_name=product_name,
        batch_no=batch_no,
        risk_level=risk_level,
        root_cause_suggestion=root_cause,
        description=description,
    )

    try:
        res: Dict[str, Any] = call_json(
            llm_callable=call_llama,
            prompt=user_prompt,
            system=CAPA_SYSTEM_PROMPT,
            max_retries=1,
        )

        corr = res.get("corrective_action", "")
        prev = res.get("preventive_action", "")
        framing = res.get("framing_note", "Draft CAPA recommendation for QA Reviewer evaluation.")

        if not corr or not prev:
            formatted_capa = _heuristic_capa(extracted, root_cause, risk_level)
        else:
            formatted_capa = (
                f"[DRAFT CAPA RECOMMENDATION — FOR QA REVIEWER EVALUATION]\n\n"
                f"1. CORRECTIVE ACTION (Immediate Containment):\n{corr}\n\n"
                f"2. PREVENTIVE ACTION (Systemic Long-Term Fix):\n{prev}\n\n"
                f"Disclaimer: {framing}"
            )

        state["capa_suggestion"] = formatted_capa
        return state

    except Exception as exc:
        logger.warning("capa_recommender_node_sync LLM error: %s. Using heuristic fallback.", exc)
        state["capa_suggestion"] = _heuristic_capa(extracted, root_cause, risk_level)
        return state
