"""
app/agents/graph.py
-------------------
LangGraph Agent Pipeline Assembly.

Topology:
  [START]
     │
     ▼
┌──────────────────────┐
│  intake_parser       │  (Gemma 2 9B IT: extracts structured JSON fields)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ completeness_checker │  (Rules + Gemma 2 9B IT: flags missing fields / vague desc)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   risk_classifier    │  (Llama 3.3 70B: GXP Risk level - Critical/Major/Minor)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  duplicate_detector  │  (PostgreSQL candidate query + TF-IDF Cosine Similarity)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ root_cause_recommender│ (Llama 3.3 70B: 5M Ishikawa root cause hypotheses)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   capa_recommender   │  (Llama 3.3 70B: 2-part Corrective & Preventive Action draft)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  summary_generator   │  (Gemma 2 9B IT: 2-3 sentence executive briefing)
└──────────┬───────────┘
           │
           ▼
        [ END ]
"""

import logging
from typing import Any, Dict, Optional

from langgraph.graph import END, StateGraph
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
# Graph Builder
# ---------------------------------------------------------------------------

def build_complaint_graph(
    db_session: Optional[AsyncSession] = None,
    similarity_threshold: float = 0.75,
):
    """
    Constructs and compiles the full LangGraph StateGraph pipeline.

    Parameters
    ----------
    db_session : AsyncSession
        Active database session to supply to the duplicate_detector node factory.
    similarity_threshold : float
        Duplicate detection similarity cutoff.

    Returns
    -------
    Compiled StateGraph runnable.
    """
    builder = StateGraph(ComplaintState)

    # 1. Register nodes
    builder.add_node("intake_parser", intake_parser_node)
    builder.add_node("completeness_checker", completeness_checker_node)
    builder.add_node("risk_classifier", risk_classifier_node)

    # Inject DB session into duplicate detector factory
    duplicate_detector_fn = make_duplicate_detector_node(
        db=db_session, similarity_threshold=similarity_threshold
    )
    builder.add_node("duplicate_detector", duplicate_detector_fn)

    builder.add_node("root_cause_recommender", root_cause_recommender_node)
    builder.add_node("capa_recommender", capa_recommender_node)
    builder.add_node("summary_generator", summary_generator_node)

    # 2. Define linear edge topology
    builder.set_entry_point("intake_parser")
    builder.add_edge("intake_parser", "completeness_checker")
    builder.add_edge("completeness_checker", "risk_classifier")
    builder.add_edge("risk_classifier", "duplicate_detector")
    builder.add_edge("duplicate_detector", "root_cause_recommender")
    builder.add_edge("root_cause_recommender", "capa_recommender")
    builder.add_edge("capa_recommender", "summary_generator")
    builder.add_edge("summary_generator", END)

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

    Parameters
    ----------
    raw_text : str
        The raw text from complaint intake form, email body, or extracted document.
    db_session : AsyncSession, optional
        Active SQLAlchemy async database session for duplicate search.
    complaint_id : int, optional
        ID of the complaint if already created in DB (excludes itself from duplicate search).
    similarity_threshold : float
        Cutoff for duplicate detection (default 0.75).

    Returns
    -------
    Dict representing the final populated `ComplaintState`.
    """
    logger.info("Starting run_complaint_pipeline for text len=%d", len(raw_text or ""))

    initial_state: ComplaintState = {
        "raw_text": raw_text or "",
        "complaint_id": complaint_id,
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


def run_complaint_pipeline_sync(
    raw_text: str,
    db_session: Optional[AsyncSession] = None,
    complaint_id: Optional[int] = None,
    similarity_threshold: float = 0.75,
) -> Dict[str, Any]:
    """
    Synchronous fallback runner executing node functions sequentially.
    Useful for offline testing or synchronous scripts.
    """
    state: ComplaintState = {
        "raw_text": raw_text or "",
        "complaint_id": complaint_id,
        "extracted_fields": {},
        "completeness_flags": [],
        "risk_level": None,
        "risk_rationale": None,
        "possible_duplicates": [],
        "root_cause_suggestion": None,
        "capa_suggestion": None,
        "summary": None,
    }

    # Step 1: Intake Parser
    state = intake_parser_node_sync(state)

    # Step 2: Completeness Checker
    state = completeness_checker_node_sync(state)

    # Step 3: Risk Classifier
    state = risk_classifier_node_sync(state)

    # Step 4: Duplicate Detector (Sync wrapper logic)
    # If db_session is provided, runs async query inside an event loop
    if db_session:
        import asyncio

        node_fn = make_duplicate_detector_node(
            db=db_session, similarity_threshold=similarity_threshold
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async loop
                state["possible_duplicates"] = []
            else:
                state = loop.run_until_complete(node_fn(state))
        except Exception:
            state["possible_duplicates"] = []
    else:
        state["possible_duplicates"] = []

    # Step 5: Root Cause Recommender
    state = root_cause_recommender_node_sync(state)

    # Step 6: CAPA Recommender
    state = capa_recommender_node_sync(state)

    # Step 7: Summary Generator
    state = summary_generator_node_sync(state)

    return dict(state)
