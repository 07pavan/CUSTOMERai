"""
app/agents/nodes/summary_generator.py
---------------------------------------
LangGraph Node: Summary Generator

Produces a 2-3 sentence executive summary of the complaint and AI triage assessment
using Gemma 2 9B IT (`gemma2-9b-it`).

Synthesizes:
  - Product & batch identification
  - Reported quality defect / clinical issue
  - Assigned GXP risk level & completeness status
  - Duplicate detection finding & primary root cause hypothesis

Output:
  - state["summary"] : Concise 2-3 sentence executive summary.
"""

import logging
from typing import Any, Dict

from app.agents.llm import acall_gemma, call_gemma
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SUMMARY_SYSTEM_PROMPT = """
You are a Pharmaceutical QA Executive Assistant specializing in executive triage briefings.
Your job is to synthesize all technical findings of a complaint assessment into a crisp 2-3 sentence executive summary for a QA Reviewer.

EXECUTIVE SUMMARY REQUIREMENTS:
- Sentence 1: Identify the product name, batch/lot number, reporter, and brief defect description.
- Sentence 2: State the assigned GXP risk level (Critical, Major, or Minor) and key risk rationale.
- Sentence 3: Mention if any completeness flags or potential duplicates were detected, along with the leading 5M root cause hypothesis.
- Keep it concise, formal, and objective. Maximum 40-70 words. Do NOT use bullet points or extra headers.
"""

SUMMARY_USER_TEMPLATE = """
Synthesize a 2-3 sentence executive summary for the following complaint assessment:

Product Name: {product_name}
Batch Number: {batch_no}
Reporter: {complainant_name} ({complainant_contact})
Category: {category}
Description: {description}
Assigned Risk Level: {risk_level}
Risk Rationale: {risk_rationale}
Completeness Issues: {completeness_summary}
Duplicate Status: {duplicate_summary}
Root Cause Hypothesis: {root_cause_summary}
"""


# ---------------------------------------------------------------------------
# Fallback Summary Generator (Offline / Keyless Mode)
# ---------------------------------------------------------------------------

def _heuristic_summary(state: ComplaintState) -> str:
    """Generate a clean 2-3 sentence fallback summary when LLM is unavailable."""
    extracted = state.get("extracted_fields", {})
    product = extracted.get("product_name") or "Pharmaceutical product"
    batch = extracted.get("batch_no") or "unspecified lot"
    reporter = extracted.get("customer_name") or extracted.get("complainant_name") or "an anonymous reporter"
    risk = (state.get("severity") or state.get("risk_level") or "major").upper()
    category = extracted.get("complaint_category") or extracted.get("category") or "quality"
    dups = state.get("possible_duplicates", [])
    flags = state.get("completeness_flags", [])

    dup_text = f" flagged with {len(dups)} potential duplicate(s)" if dups else " no duplicates detected"
    flag_text = f", {len(flags)} completeness issue(s) identified" if flags else ""

    return (
        f"Complaint logged for {product} (Lot {batch}) reported by {reporter} regarding {category} issues. "
        f"Assessed as [{risk} RISK] based on defect severity and regulatory evaluation. "
        f"Automated screening results:{dup_text}{flag_text}; preliminary investigation dispatched to QA triage."
    )


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

async def summary_generator_node(state: ComplaintState) -> ComplaintState:
    """
    LangGraph async node: populates `state['summary']`.
    """
    extracted = state.get("extracted_fields", {})
    dups = state.get("possible_duplicates", [])
    flags = state.get("completeness_flags", [])

    product_name = extracted.get("product_name") or "Unspecified Product"
    batch_no = extracted.get("batch_no") or "Unspecified Batch"
    complainant_name = extracted.get("customer_name") or extracted.get("complainant_name") or "Anonymous Reporter"
    complainant_contact = extracted.get("complainant_contact") or "No contact provided"
    category = extracted.get("complaint_category") or extracted.get("category") or "quality"
    description = extracted.get("complaint_description") or extracted.get("description") or state.get("raw_text", "")[:300]
    risk_level = (state.get("severity") or state.get("risk_level") or "major").upper()
    risk_rationale = state.get("initial_risk_assessment") or state.get("risk_rationale") or "Standard QA review."

    completeness_summary = f"{len(flags)} flag(s): " + ", ".join([f.get("issue", "") for f in flags[:2]]) if flags else "None"
    duplicate_summary = f"{len(dups)} potential duplicate match(es) found" if dups else "None detected"
    root_cause_summary = state.get("root_cause_suggestion", "Under investigation")[:150].replace("\n", " ")

    user_prompt = SUMMARY_USER_TEMPLATE.format(
        product_name=product_name,
        batch_no=batch_no,
        complainant_name=complainant_name,
        complainant_contact=complainant_contact,
        category=category,
        description=description,
        risk_level=risk_level,
        risk_rationale=risk_rationale,
        completeness_summary=completeness_summary,
        duplicate_summary=duplicate_summary,
        root_cause_summary=root_cause_summary,
    )

    try:
        summary_text = await acall_gemma(
            prompt=user_prompt,
            system=SUMMARY_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=250,
        )
        summary_text = summary_text.strip()

        if not summary_text or len(summary_text) < 20:
            summary_text = _heuristic_summary(state)

        state["summary"] = summary_text
        logger.info("summary_generator_node completed successfully.")
        return state

    except Exception as exc:
        logger.warning("summary_generator_node LLM error: %s. Using heuristic fallback.", exc)
        state["summary"] = _heuristic_summary(state)
        return state


def summary_generator_node_sync(state: ComplaintState) -> ComplaintState:
    """
    Synchronous version of summary_generator_node.
    """
    extracted = state.get("extracted_fields", {})
    dups = state.get("possible_duplicates", [])
    flags = state.get("completeness_flags", [])

    product_name = extracted.get("product_name") or "Unspecified Product"
    batch_no = extracted.get("batch_no") or "Unspecified Batch"
    complainant_name = extracted.get("complainant_name") or "Anonymous Reporter"
    complainant_contact = extracted.get("complainant_contact") or "No contact provided"
    category = extracted.get("category") or "quality"
    description = extracted.get("description") or state.get("raw_text", "")[:300]
    risk_level = (state.get("risk_level") or "major").upper()
    risk_rationale = state.get("risk_rationale") or "Standard QA review."

    completeness_summary = f"{len(flags)} flag(s): " + ", ".join([f.get("issue", "") for f in flags[:2]]) if flags else "None"
    duplicate_summary = f"{len(dups)} potential duplicate match(es) found" if dups else "None detected"
    root_cause_summary = state.get("root_cause_suggestion", "Under investigation")[:150].replace("\n", " ")

    user_prompt = SUMMARY_USER_TEMPLATE.format(
        product_name=product_name,
        batch_no=batch_no,
        complainant_name=complainant_name,
        complainant_contact=complainant_contact,
        category=category,
        description=description,
        risk_level=risk_level,
        risk_rationale=risk_rationale,
        completeness_summary=completeness_summary,
        duplicate_summary=duplicate_summary,
        root_cause_summary=root_cause_summary,
    )

    try:
        summary_text = call_gemma(
            prompt=user_prompt,
            system=SUMMARY_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=250,
        )
        summary_text = summary_text.strip()

        if not summary_text or len(summary_text) < 20:
            summary_text = _heuristic_summary(state)

        state["summary"] = summary_text
        return state

    except Exception as exc:
        logger.warning("summary_generator_node_sync LLM error: %s. Using heuristic fallback.", exc)
        state["summary"] = _heuristic_summary(state)
        return state
