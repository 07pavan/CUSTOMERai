"""
app/agents/graph.py
-------------------
LangGraph Agent Pipeline Assembly with Intent Routing & Field Correction.

Topology:
                  [ START ]
                      │
           (intent_router conditional edge)
           ┌──────────┴──────────┐
  "new_complaint"           "correction"
           │                     │
           ▼                     ▼
 ┌──────────────────┐  ┌──────────────────┐
 │ intake_parser    │  │ field_correction │
 └─────────┬────────┘  └─────────┬────────┘
           │                     │
           ▼                     │
 ┌──────────────────┐            │
 │completeness_chkr │            │
 └─────────┬────────┘            │
           │                     │
           ▼                     │
 ┌──────────────────┐            │
 │ risk_classifier  │            │
 └─────────┬────────┘            │
           │                     │
           ▼                     │
 ┌──────────────────┐            │
 │duplicate_detector│            │
 └─────────┬────────┘            │
           │                     │
           ▼                     │
 ┌──────────────────┐            │
 │root_cause_recomm │            │
 └─────────┬────────┘            │
           │                     │
           ▼                     │
 ┌──────────────────┐            │
 │ capa_recommender │            │
 └─────────┬────────┘            │
           │                     │
           ▼                     │
 ┌──────────────────┐            │
 │summary_generator │            │
 └─────────┬────────┘            │
           │                     │
           ▼                     ▼
        [ END ]               [ END ]
"""

import logging
from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.nodes.capa_recommender import (
    capa_recommender_node,
    capa_recommender_node_sync,
)
from app.agents.nodes.completeness_checker import (
    completeness_checker_node,
    completeness_checker_node_sync,
)
from app.agents.nodes.duplicate_detector import make_duplicate_detector_node
from app.agents.nodes.field_correction import (
    field_correction_node,
    field_correction_node_sync,
)
from app.agents.nodes.intake_parser import intake_parser_node, intake_parser_node_sync
from app.agents.nodes.risk_classifier import (
    risk_classifier_node,
    risk_classifier_node_sync,
)
from app.agents.nodes.root_cause_recommender import (
    root_cause_recommender_node,
    root_cause_recommender_node_sync,
)
from app.agents.nodes.summary_generator import (
    summary_generator_node,
    summary_generator_node_sync,
)
from app.agents.state import ComplaintState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent Router
# ---------------------------------------------------------------------------

def intent_router(state: ComplaintState) -> str:
    """
    Decides whether the message is a new complaint intake vs a correction to an active complaint.
    Returns 'correction' or 'new_complaint'.
    """
    if state.get("is_correction") or state.get("correction_message"):
        return "correction"

    raw = (state.get("raw_text") or state.get("incoming_message") or "").strip().lower()
    if state.get("complaint_id") or state.get("extracted_fields"):
        correction_keywords = [
            "sorry", "correction", "actually", "batch number is", "lot is",
            "quantity is", "change", "update batch", "correct the", "wrong quantity"
        ]
        if any(kw in raw for kw in correction_keywords) and len(raw) < 150:
            return "correction"

    return "new_complaint"


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

def build_complaint_graph(
    db_session: Optional[AsyncSession] = None,
    similarity_threshold: float = 0.75,
):
    """
    Constructs and compiles the full LangGraph StateGraph pipeline with intent routing.
    """
    builder = StateGraph(ComplaintState)

    # 1. Register nodes
    builder.add_node("intake_parser", intake_parser_node)
    builder.add_node("completeness_checker", completeness_checker_node)
    builder.add_node("risk_classifier", risk_classifier_node)

    duplicate_detector_fn = make_duplicate_detector_node(
        db=db_session, similarity_threshold=similarity_threshold
    )
    builder.add_node("duplicate_detector", duplicate_detector_fn)

    builder.add_node("root_cause_recommender", root_cause_recommender_node)
    builder.add_node("capa_recommender", capa_recommender_node)
    builder.add_node("summary_generator", summary_generator_node)
    builder.add_node("field_correction", field_correction_node)

    # 2. Define conditional entry topology via intent_router
    builder.add_conditional_edges(
        START,
        intent_router,
        {
            "new_complaint": "intake_parser",
            "correction": "field_correction",
        },
    )

    # 3. Define node transitions
    builder.add_edge("intake_parser", "completeness_checker")
    builder.add_edge("completeness_checker", "risk_classifier")
    builder.add_edge("risk_classifier", "duplicate_detector")
    builder.add_edge("duplicate_detector", "root_cause_recommender")
    builder.add_edge("root_cause_recommender", "capa_recommender")
    builder.add_edge("capa_recommender", "summary_generator")
    builder.add_edge("summary_generator", END)
    builder.add_edge("field_correction", END)

    return builder.compile()


# ---------------------------------------------------------------------------
# High-Level Execution Entry Points
# ---------------------------------------------------------------------------

async def run_complaint_pipeline(
    raw_text: str,
    db_session: Optional[AsyncSession] = None,
    complaint_id: Optional[int] = None,
    similarity_threshold: float = 0.75,
) -> Dict[str, Any]:
    """
    Asynchronous top-level entry point to execute the full complaint AI triage graph.
    """
    logger.info("Starting run_complaint_pipeline for text len=%d", len(raw_text or ""))

    initial_state: ComplaintState = {
        "raw_text": raw_text or "",
        "complaint_id": complaint_id,
        "is_correction": False,
        "extracted_fields": {},
        "completeness_flags": [],
        "risk_level": None,
        "risk_rationale": None,
        "possible_duplicates": [],
        "root_cause_suggestion": None,
        "capa_suggestion": None,
        "summary": None,
    }

    graph = build_complaint_graph(
        db_session=db_session, similarity_threshold=similarity_threshold
    )

    final_state = await graph.ainvoke(initial_state)
    logger.info("run_complaint_pipeline finished successfully.")
    return dict(final_state)


async def apply_correction(
    existing_fields: Dict[str, Any],
    correction_message: str,
) -> Dict[str, Any]:
    """
    Applies a user correction message to an existing extracted_fields dictionary.

    Returns
    -------
    Dict containing:
      - 'field_diff'       : Only the fields that changed
      - 'extracted_fields' : Merged updated field dictionary
    """
    logger.info("Starting apply_correction for message: '%s'", correction_message)

    initial_state: ComplaintState = {
        "is_correction": True,
        "correction_message": correction_message,
        "raw_text": correction_message,
        "extracted_fields": existing_fields or {},
        "field_diff": {},
    }

    graph = build_complaint_graph()
    final_state = await graph.ainvoke(initial_state)
    return {
        "field_diff": final_state.get("field_diff", {}),
        "extracted_fields": final_state.get("extracted_fields", {}),
    }


def apply_correction_sync(
    existing_fields: Dict[str, Any],
    correction_message: str,
) -> Dict[str, Any]:
    """
    Synchronous version of apply_correction.
    """
    state: ComplaintState = {
        "is_correction": True,
        "correction_message": correction_message,
        "raw_text": correction_message,
        "extracted_fields": existing_fields or {},
        "field_diff": {},
    }
    state = field_correction_node_sync(state)
    return {
        "field_diff": state.get("field_diff", {}),
        "extracted_fields": state.get("extracted_fields", {}),
    }


def run_complaint_pipeline_sync(
    raw_text: str,
    db_session: Optional[AsyncSession] = None,
    complaint_id: Optional[int] = None,
    similarity_threshold: float = 0.75,
) -> Dict[str, Any]:
    """
    Synchronous fallback runner executing node functions sequentially.
    """
    state: ComplaintState = {
        "raw_text": raw_text or "",
        "complaint_id": complaint_id,
        "is_correction": False,
        "extracted_fields": {},
        "completeness_flags": [],
        "risk_level": None,
        "risk_rationale": None,
        "possible_duplicates": [],
        "root_cause_suggestion": None,
        "capa_suggestion": None,
        "summary": None,
    }

    state = intake_parser_node_sync(state)
    state = completeness_checker_node_sync(state)
    state = risk_classifier_node_sync(state)

    if db_session:
        import asyncio
        node_fn = make_duplicate_detector_node(
            db=db_session, similarity_threshold=similarity_threshold
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                state["possible_duplicates"] = []
            else:
                state = loop.run_until_complete(node_fn(state))
        except Exception:
            state["possible_duplicates"] = []
    else:
        state["possible_duplicates"] = []

    state = root_cause_recommender_node_sync(state)
    state = capa_recommender_node_sync(state)
    state = summary_generator_node_sync(state)

    return dict(state)
