"""
app/agents/nodes/risk_classifier.py
------------------------------------
LangGraph Node: Risk Classifier

Classifies the pharmaceutical risk level of a complaint using Llama 3.3 70B Versatile.

Outputs:
  - state["severity"]                : 'critical' | 'major' | 'minor'
  - state["suggested_next_action"]   : Short actionable phrase for QA triage
  - state["initial_risk_assessment"] : 1-2 sentence medical / QA regulatory justification
  - state["risk_level"]              : Alias for severity (downstream compatibility)
  - state["risk_rationale"]          : Alias for initial_risk_assessment (downstream compatibility)
"""

import logging
from typing import Any, Dict

from app.agents.llm import acall_json, acall_llama, call_json, call_llama
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)

ALLOWED_SEVERITIES = {"critical", "major", "minor"}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

RISK_CLASSIFIER_SYSTEM_PROMPT = """
You are a Senior Pharmaceutical Quality Assurance & Pharmacovigilance Regulatory Officer.
Your responsibility is to evaluate incoming customer complaints and produce a risk classification.

CLASSIFICATION RULES:
1. "critical":
   - Suspected counterfeit, falsified packaging, or altered security seals.
   - Any report of adverse patient events, toxicity, hospitalization, or harm.
   - Foreign particulate matter in sterile, parenteral, or injectable products.
   - Cross-contamination or strength/dosage form mix-up.

2. "major":
   - Quality defects affecting drug efficacy, active ingredient degradation, or dose uniformity (e.g. discolored tablets, chipped ER tablets).
   - Defective primary packaging compromising moisture/oxygen protection (e.g. unsealed blister foils).

3. "minor":
   - Cosmetic flaws on outer shipping boxes, minor label printing misalignment, or secondary packaging smudges.

JSON RESPONSE FORMAT:
Respond ONLY with a single JSON object:
{
  "severity": "critical" | "major" | "minor",
  "suggested_next_action": "A short (4-10 word) actionable triage recommendation.",
  "initial_risk_assessment": "1-2 concise sentences explaining the medical or regulatory justification."
}
"""

RISK_CLASSIFIER_USER_TEMPLATE = """
Classify the risk level of the following pharmaceutical complaint:

Product Name: {product_name}
Product Strength: {product_strength}
Category: {category}
Description / Details:
{description}

Raw Document Excerpt:
{raw_text_snippet}
"""


# ---------------------------------------------------------------------------
# Heuristic Fallback
# ---------------------------------------------------------------------------

def _heuristic_risk_classifier(extracted: Dict[str, Any], raw_text: str) -> Dict[str, str]:
    cat = (extracted.get("complaint_category") or extracted.get("category") or "").lower().strip()
    text = (raw_text + " " + (extracted.get("complaint_description") or extracted.get("description") or "") + " " + (extracted.get("product_name") or "")).lower()

    if cat == "counterfeit" or any(w in text for w in ["counterfeit", "fake", "hologram", "particulate", "injection", "vial", "sterile", "adverse_event", "mix-up", "mixup", "wrong capsule"]):
        return {
            "severity": "critical",
            "suggested_next_action": "Issue immediate quarantine hold and initiate brand protection / security protocol.",
            "initial_risk_assessment": "Potential patient safety hazard or suspected counterfeit packaging requiring immediate GXP escalation.",
        }

    if cat in ("quality", "adverse_event") or any(w in text for w in ["discolored", "chipped", "crumble", "seal", "defect", "broken"]):
        return {
            "severity": "major",
            "suggested_next_action": "Pull retain samples for lab assay and perform batch trend evaluation.",
            "initial_risk_assessment": "Product quality defect impacting dose uniformity or packaging integrity without acute patient toxicity reported.",
        }

    return {
        "severity": "minor",
        "suggested_next_action": "Log complaint for monthly QA quality metrics review.",
        "initial_risk_assessment": "Cosmetic or minor packaging variation with no impact on product efficacy or patient safety.",
    }


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

async def risk_classifier_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: sets `severity`, `suggested_next_action`, and `initial_risk_assessment`.
    """
    extracted = state.get("extracted_fields", {})
    raw_text = state.get("raw_text", "")

    product_name = extracted.get("product_name") or "Unspecified Product"
    product_strength = extracted.get("product_strength") or "N/A"
    category = extracted.get("complaint_category") or extracted.get("category") or "quality"
    description = extracted.get("complaint_description") or extracted.get("description") or raw_text[:400] or "No description provided."

    user_prompt = RISK_CLASSIFIER_USER_TEMPLATE.format(
        product_name=product_name,
        product_strength=product_strength,
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

        sev = (res.get("severity") or res.get("risk_level") or "").strip().lower()
        next_action = (res.get("suggested_next_action") or "").strip()
        rationale = (res.get("initial_risk_assessment") or res.get("risk_rationale") or "").strip()

        if sev not in ALLOWED_SEVERITIES:
            sev = "major"
        if not next_action:
            next_action = "Initiate QA investigation and retain sample review."
        if not rationale:
            rationale = "Defaulted to Major risk pending human QA review."

        _populate_state_risk(state, sev, next_action, rationale)
        logger.info("risk_classifier_node completed: severity='%s'", sev)
        return state

    except Exception as exc:
        logger.warning("risk_classifier_node LLM error: %s. Using heuristic fallback.", exc)
        fallback = _heuristic_risk_classifier(extracted, raw_text)
        _populate_state_risk(state, fallback["severity"], fallback["suggested_next_action"], fallback["initial_risk_assessment"])
        return state


def risk_classifier_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of risk_classifier_node for standalone testing.
    """
    extracted = state.get("extracted_fields", {})
    raw_text = state.get("raw_text", "")

    product_name = extracted.get("product_name") or "Unspecified Product"
    product_strength = extracted.get("product_strength") or "N/A"
    category = extracted.get("complaint_category") or extracted.get("category") or "quality"
    description = extracted.get("complaint_description") or extracted.get("description") or raw_text[:400] or "No description provided."

    user_prompt = RISK_CLASSIFIER_USER_TEMPLATE.format(
        product_name=product_name,
        product_strength=product_strength,
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

        sev = (res.get("severity") or res.get("risk_level") or "").strip().lower()
        next_action = (res.get("suggested_next_action") or "").strip()
        rationale = (res.get("initial_risk_assessment") or res.get("risk_rationale") or "").strip()

        if sev not in ALLOWED_SEVERITIES:
            sev = "major"
        if not next_action:
            next_action = "Initiate QA investigation and retain sample review."
        if not rationale:
            rationale = "Defaulted to Major risk pending human QA review."

        _populate_state_risk(state, sev, next_action, rationale)
        return state

    except Exception as exc:
        logger.warning("risk_classifier_node_sync LLM error: %s. Using heuristic fallback.", exc)
        fallback = _heuristic_risk_classifier(extracted, raw_text)
        _populate_state_risk(state, fallback["severity"], fallback["suggested_next_action"], fallback["initial_risk_assessment"])
        return state


def _populate_state_risk(state: ComplaintState, severity: str, next_action: str, rationale: str) -> None:
    state["severity"] = severity
    state["suggested_next_action"] = next_action
    state["initial_risk_assessment"] = rationale

    # Backward compatibility aliases
    state["risk_level"] = severity
    state["risk_rationale"] = rationale
