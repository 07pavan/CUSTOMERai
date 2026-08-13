"""
app/agents/nodes/risk_classifier.py
------------------------------------
LangGraph Node: Risk Classifier

Classifies the pharmaceutical risk level of a complaint using Llama 3.3 70B Versatile
(`llama-3.3-70b-versatile`).

Risk Level Hierarchy (GXP / 21 CFR Compliant):
  - CRITICAL : Potential patient safety hazard, adverse event, sterile product contamination,
               injectable particulate matter, dosage mix-up, or suspected counterfeit.
  - MAJOR    : Quality defect affecting product efficacy, dose uniformity, or active ingredient
               degradation without immediate life-threatening safety signal (e.g. chipped ER tablets,
               tablet discoloration, active seal degradation).
  - MINOR    : Cosmetic, labeling alignment, or tertiary packaging issue with zero impact on product
               safety, sterility, or therapeutic efficacy.

Outputs:
  - state["risk_level"]     : 'critical' | 'major' | 'minor' (defaults to 'major' on invalid output)
  - state["risk_rationale"] : 1-2 sentence medical / QA regulatory justification
"""

import logging
from typing import Any, Dict

from app.agents.llm import acall_json, acall_llama, call_json, call_llama
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)

ALLOWED_RISK_LEVELS = {"critical", "major", "minor"}


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

RISK_CLASSIFIER_SYSTEM_PROMPT = """
You are a Senior Pharmaceutical Quality Assurance & Pharmacovigilance Regulatory Officer.
Your responsibility is to classify incoming customer complaints into the correct regulatory risk category.

CLASSIFICATION RULES:
1. "critical":
   - Suspected counterfeit, falsified packaging, or altered security seals.
   - Any report of adverse patient events, toxicity, hospitalization, or harm.
   - Foreign particulate matter in sterile, parenteral, or injectable products.
   - Cross-contamination or strength/dosage form mix-up (e.g. 10mg capsule inside a 5mg bottle).

2. "major":
   - Quality defects affecting drug efficacy, active ingredient degradation, or dose uniformity (e.g. discolored tablets, chipped extended-release tablets).
   - Defective primary packaging compromising moisture/oxygen protection (e.g. unsealed blister foils).
   - No immediate acute life-threatening patient event reported, but product is out-of-specification.

3. "minor":
   - Cosmetic flaws on outer shipping boxes, minor label printing misalignment, or secondary packaging smudges.
   - Zero impact on drug efficacy, potency, sterility, or patient safety.

JSON RESPONSE FORMAT:
Respond ONLY with a single JSON object:
{
  "risk_level": "critical" | "major" | "minor",
  "risk_rationale": "1-2 concise sentences explaining the medical or regulatory justification."
}
"""

RISK_CLASSIFIER_USER_TEMPLATE = """
Classify the risk level of the following pharmaceutical complaint:

Product Name: {product_name}
Category: {category}
Description / Details:
{description}

Raw Document Excerpt:
{raw_text_snippet}
"""


# ---------------------------------------------------------------------------
# Heuristic Fallback (for offline or unconfigured API key testing)
# ---------------------------------------------------------------------------

def _heuristic_risk_classifier(extracted: Dict[str, Any], raw_text: str) -> Dict[str, str]:
    """
    Deterministic rule-based risk classifier used when the LLM is offline.
    Ensures tests and pipeline execution succeed even without a Groq API key.
    """
    cat = (extracted.get("category") or "").lower().strip()
    text = (raw_text + " " + (extracted.get("description") or "") + " " + (extracted.get("product_name") or "")).lower()

    # Critical triggers
    if cat == "counterfeit" or any(w in text for w in ["counterfeit", "fake", "hologram", "particulate", "injection", "vial", "sterile", "adverse_event", "mix-up", "mixup", "wrong capsule"]):
        return {
            "risk_level": "critical",
            "risk_rationale": "Potential patient safety hazard or suspected counterfeit packaging requiring immediate GXP escalation.",
        }

    # Major triggers
    if cat in ("quality", "adverse_event") or any(w in text for w in ["discolored", "chipped", "crumble", "seal", "defect", "broken"]):
        return {
            "risk_level": "major",
            "risk_rationale": "Product quality defect impacting dose uniformity or packaging integrity without acute patient toxicity reported.",
        }

    # Minor default
    return {
        "risk_level": "minor",
        "risk_rationale": "Cosmetic or minor packaging variation with no impact on product efficacy or patient safety.",
    }


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

async def risk_classifier_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: classifies `risk_level` and `risk_rationale` using Llama 3.3 70B.

    Parameters
    ----------
    state : ComplaintState

    Returns
    -------
    Updated ComplaintState with `risk_level` and `risk_rationale` set.
    """
    extracted = state.get("extracted_fields", {})
    raw_text = state.get("raw_text", "")

    product_name = extracted.get("product_name") or "Unspecified Product"
    category = extracted.get("category") or "quality"
    description = extracted.get("description") or raw_text[:400] or "No description provided."

    user_prompt = RISK_CLASSIFIER_USER_TEMPLATE.format(
        product_name=product_name,
        category=category,
        description=description,
        raw_text_snippet=raw_text[:500],
    )

    try:
        res: Dict[str, Any] = await acall_json(
            async_llm_callable=acall_llama,
            prompt=user_prompt,
            system=RISK_CLASSIFIER_SYSTEM_PROMPT,
            max_retries=1,
        )

        raw_level = (res.get("risk_level") or "").strip().lower()
        rationale = (res.get("risk_rationale") or "").strip()

        # Validation guard: ensure risk_level is one of the allowed set
        if raw_level not in ALLOWED_RISK_LEVELS:
            logger.warning(
                "risk_classifier_node: LLM returned invalid risk_level '%s'. Defaulting to 'major'.",
                raw_level,
            )
            raw_level = "major"
            if not rationale:
                rationale = "Defaulted to Major risk pending human QA review due to unrecognised classification label."

        state["risk_level"] = raw_level
        state["risk_rationale"] = rationale

        logger.info(
            "risk_classifier_node completed: risk_level='%s'", raw_level
        )
        return state

    except Exception as exc:
        logger.warning(
            "risk_classifier_node LLM error: %s. Using heuristic fallback.", exc
        )
        fallback = _heuristic_risk_classifier(extracted, raw_text)
        state["risk_level"] = fallback["risk_level"]
        state["risk_rationale"] = fallback["risk_rationale"]
        return state


def risk_classifier_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of risk_classifier_node for standalone testing.
    """
    extracted = state.get("extracted_fields", {})
    raw_text = state.get("raw_text", "")

    product_name = extracted.get("product_name") or "Unspecified Product"
    category = extracted.get("category") or "quality"
    description = extracted.get("description") or raw_text[:400] or "No description provided."

    user_prompt = RISK_CLASSIFIER_USER_TEMPLATE.format(
        product_name=product_name,
        category=category,
        description=description,
        raw_text_snippet=raw_text[:500],
    )

    try:
        res: Dict[str, Any] = call_json(
            llm_callable=call_llama,
            prompt=user_prompt,
            system=RISK_CLASSIFIER_SYSTEM_PROMPT,
            max_retries=1,
        )

        raw_level = (res.get("risk_level") or "").strip().lower()
        rationale = (res.get("risk_rationale") or "").strip()

        if raw_level not in ALLOWED_RISK_LEVELS:
            logger.warning(
                "risk_classifier_node_sync: LLM returned invalid risk_level '%s'. Defaulting to 'major'.",
                raw_level,
            )
            raw_level = "major"
            if not rationale:
                rationale = "Defaulted to Major risk pending human QA review due to unrecognised classification label."

        state["risk_level"] = raw_level
        state["risk_rationale"] = rationale
        return state

    except Exception as exc:
        logger.warning(
            "risk_classifier_node_sync LLM error: %s. Using heuristic fallback.", exc
        )
        fallback = _heuristic_risk_classifier(extracted, raw_text)
        state["risk_level"] = fallback["risk_level"]
        state["risk_rationale"] = fallback["risk_rationale"]
        return state
