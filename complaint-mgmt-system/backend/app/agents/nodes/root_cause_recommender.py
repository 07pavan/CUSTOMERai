"""
app/agents/nodes/root_cause_recommender.py
-------------------------------------------
LangGraph Node: Root Cause Recommender

Analyzes the complaint details and uses Llama 3.3 70B (`llama-3.3-70b-versatile`) to
hypothesize 1-3 potential root cause categories using the 5M Ishikawa Framework:
  - Man        : Training, human error, operator fatigue, procedure deviation.
  - Machine    : Calibration error, mechanical failure, seal wear, tooling defect.
  - Material   : Raw material impurity, API supplier defect, primary packaging flaw.
  - Method     : Inadequate SOP, process validation gap, improper cleanroom protocol.
  - Environment: Humidity fluctuation, cleanroom HVAC particulate surge, temperature excursion.

Regulatory Framing (21 CFR Part 211 / GXP):
Output MUST be explicitly framed as preliminary investigation hypotheses, NOT confirmed findings.

Output:
  - state["root_cause_suggestion"] : Formatted string with 5M categories and explanations.
"""

import logging
from typing import Any, Dict, List, Optional

from app.agents.llm import acall_json, acall_llama, call_json, call_llama
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

ROOT_CAUSE_SYSTEM_PROMPT = """
You are an expert Pharmaceutical Quality Assurance Investigation Manager and RCA Lead.
Your task is to analyze a customer quality complaint and suggest 1-3 preliminary root cause hypotheses using the standard 5M Framework (Man, Machine, Material, Method, Environment).

RULES:
1. Select 1 to 3 relevant categories strictly from the 5M Framework:
   - "Material"
   - "Machine"
   - "Method"
   - "Man"
   - "Environment"
2. Provide a 1-line concise technical explanation for each chosen category based on the defect description.
3. CRITICAL REGULATORY FRAMING: State clearly in your response that these are PRELIMINARY HYPOTHESES to guide the investigation, NOT confirmed findings.

JSON RESPONSE FORMAT:
Respond ONLY with a single JSON object:
{
  "hypotheses": [
    {
      "category": "Material | Machine | Method | Man | Environment",
      "explanation": "One-line technical explanation grounded in the complaint details."
    }
  ],
  "disclaimer": "Preliminary investigation hypotheses for QA review. Requires laboratory verification."
}
"""

ROOT_CAUSE_USER_TEMPLATE = """
Suggest 5M root cause hypotheses for the following pharmaceutical complaint:

Product Name: {product_name}
Category: {category}
Risk Level: {risk_level}
Description:
{description}
"""


# ---------------------------------------------------------------------------
# Fallback Heuristic (Offline / Keyless Mode)
# ---------------------------------------------------------------------------

def _heuristic_root_cause(extracted: Dict[str, Any], risk_level: str) -> str:
    """Fallback 5M hypotheses when LLM is unavailable."""
    category = (extracted.get("category") or "").lower()
    desc = (extracted.get("description") or "").lower()

    hypotheses = []
    if "counterfeit" in category or "hologram" in desc or "fake" in desc:
        hypotheses.append("Material — Possible unauthorized secondary supply chain infiltration or counterfeit packaging vendor.")
        hypotheses.append("Method — Inadequate anti-counterfeiting serialization verification at receipt.")
    elif "particulate" in desc or "vial" in desc or "injection" in desc:
        hypotheses.append("Material — Stopper elastomer degradation or raw material bulk API particulate contamination.")
        hypotheses.append("Environment — Cleanroom HVAC HEPA filtration surge or laminar air flow degradation.")
        hypotheses.append("Machine — Mechanical wear on filling pump seals or glass vial washing nozzles.")
    elif "chipped" in desc or "broken" in desc or "crumble" in desc:
        hypotheses.append("Machine — Tablet press compression force variance or friability tooling alignment defect.")
        hypotheses.append("Material — Granulation binder formulation ratio error leading to high tablet friability.")
    elif "seal" in desc or "pouch" in desc or "blister" in desc:
        hypotheses.append("Machine — Packaging line heat-sealer temperature controller drift or jaw pressure misalignment.")
        hypotheses.append("Method — Packaging machine setup parameters deviation during lot startup.")
    else:
        hypotheses.append("Material — Possible raw material or primary packaging lot defect requiring retain sample analysis.")
        hypotheses.append("Machine — Equipment parameter variance during batch manufacturing.")

    formatted = "\n".join([f"• {h}" for h in hypotheses])
    return (
        f"[Preliminary Investigation Hypotheses — Subject to Lab Verification]\n"
        f"{formatted}\n\n"
        f"Note: These suggestions are generated to assist QA investigators in root-cause tree mapping."
    )


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

async def root_cause_recommender_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: populates `state['root_cause_suggestion']`.
    """
    extracted = state.get("extracted_fields", {})
    risk_level = (state.get("risk_level") or "major").upper()

    product_name = extracted.get("product_name") or "Pharmaceutical Product"
    category = extracted.get("category") or "quality"
    description = extracted.get("description") or state.get("raw_text", "")[:400]

    user_prompt = ROOT_CAUSE_USER_TEMPLATE.format(
        product_name=product_name,
        category=category,
        risk_level=risk_level,
        description=description,
    )

    try:
        res: Dict[str, Any] = await acall_json(
            async_llm_callable=acall_llama,
            prompt=user_prompt,
            system=ROOT_CAUSE_SYSTEM_PROMPT,
            max_retries=1,
        )

        hypotheses: List[Dict[str, str]] = res.get("hypotheses", [])
        disclaimer = res.get("disclaimer", "Preliminary investigation hypotheses for QA review.")

        if not hypotheses:
            formatted_suggestion = _heuristic_root_cause(extracted, risk_level)
        else:
            lines = [f"• {item.get('category', 'Material')} — {item.get('explanation', '')}" for item in hypotheses]
            formatted_suggestion = (
                f"[Preliminary Investigation Hypotheses — Subject to Lab Verification]\n"
                + "\n".join(lines)
                + f"\n\nNote: {disclaimer}"
            )

        state["root_cause_suggestion"] = formatted_suggestion
        logger.info("root_cause_recommender_node completed successfully.")
        return state

    except Exception as exc:
        logger.warning("root_cause_recommender_node LLM error: %s. Using heuristic fallback.", exc)
        state["root_cause_suggestion"] = _heuristic_root_cause(extracted, risk_level)
        return state


def root_cause_recommender_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of root_cause_recommender_node for standalone testing.
    """
    extracted = state.get("extracted_fields", {})
    risk_level = (state.get("risk_level") or "major").upper()

    product_name = extracted.get("product_name") or "Pharmaceutical Product"
    category = extracted.get("category") or "quality"
    description = extracted.get("description") or state.get("raw_text", "")[:400]

    user_prompt = ROOT_CAUSE_USER_TEMPLATE.format(
        product_name=product_name,
        category=category,
        risk_level=risk_level,
        description=description,
    )

    try:
        res: Dict[str, Any] = call_json(
            llm_callable=call_llama,
            prompt=user_prompt,
            system=ROOT_CAUSE_SYSTEM_PROMPT,
            max_retries=1,
        )

        hypotheses: List[Dict[str, str]] = res.get("hypotheses", [])
        disclaimer = res.get("disclaimer", "Preliminary investigation hypotheses for QA review.")

        if not hypotheses:
            formatted_suggestion = _heuristic_root_cause(extracted, risk_level)
        else:
            lines = [f"• {item.get('category', 'Material')} — {item.get('explanation', '')}" for item in hypotheses]
            formatted_suggestion = (
                f"[Preliminary Investigation Hypotheses — Subject to Lab Verification]\n"
                + "\n".join(lines)
                + f"\n\nNote: {disclaimer}"
            )

        state["root_cause_suggestion"] = formatted_suggestion
        return state

    except Exception as exc:
        logger.warning("root_cause_recommender_node_sync LLM error: %s. Using heuristic fallback.", exc)
        state["root_cause_suggestion"] = _heuristic_root_cause(extracted, risk_level)
        return state
