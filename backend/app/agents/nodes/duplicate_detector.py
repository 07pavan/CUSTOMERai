"""
app/agents/nodes/duplicate_detector.py
---------------------------------------
LangGraph Node: Duplicate Detector

Identifies potential duplicate complaints by comparing the incoming complaint against
existing complaints stored in PostgreSQL for the same `product_name` or `batch_no`.

───────────────────────────────────────────────────────────────────────────────
 TRADEOFF EXPLANATION: TF-IDF + Cosine Similarity vs. LLM Embeddings API
───────────────────────────────────────────────────────────────────────────────
1. TF-IDF + Cosine Similarity (Chosen Implementation via scikit-learn):
   - PROS : Extremely fast (sub-millisecond), zero API cost, 100% deterministic,
            no rate limits, runs completely locally without external dependencies.
   - CONS : Relies on exact/n-gram word overlap; can miss high-level semantic
            paraphrasing if vocabulary doesn't overlap (e.g. "pill broke" vs
            "tablet fragmented").

2. LLM Embeddings API (e.g., OpenAI text-embedding-3 / Cohere / HuggingFace):
   - PROS : Captures deep semantic similarity regardless of exact vocabulary.
   - CONS : Adds network latency (~100-300ms), incurs per-token API costs, subject
            to rate limits, and requires extra cloud credentials.

For pharmaceutical QMS, candidate complaints are pre-filtered by exact `batch_no` or
`product_name` match (narrow subset of 1-50 candidates). Within this filtered subset,
TF-IDF + Cosine Similarity delivers exceptional precision and instant performance.

───────────────────────────────────────────────────────────────────────────────
 THREADING DB SESSION THROUGH LANGGRAPH EXECUTION
───────────────────────────────────────────────────────────────────────────────
LangGraph node functions accept `state: ComplaintState` as their sole parameter.
To supply an active SQLAlchemy `AsyncSession` (and optional threshold), we use a
Higher-Order Factory Pattern (Closure):

    node = make_duplicate_detector_node(db=db_session, similarity_threshold=0.75)
    updated_state = await node(state)

This keeps node signatures clean while enabling clean dependency injection.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import ComplaintState
from app.models.complaint import Complaint

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Similarity Calculation (TF-IDF + Cosine Similarity)
# ---------------------------------------------------------------------------

def compute_similarity(text1: str, text2: str) -> float:
    """
    Compute TF-IDF Cosine Similarity between two text strings using scikit-learn.
    Returns a float between 0.0 and 1.0.
    """
    if not text1 or not text2:
        return 0.0

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        sim_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return float(sim_matrix[0][0])
    except Exception as exc:
        logger.warning("compute_similarity fallback due to error: %s", exc)
        # Fallback word-intersection Jaccard index if sklearn fails
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / float(len(set1 | set2))


# ---------------------------------------------------------------------------
# Node Factory (Injecting DB session & threshold)
# ---------------------------------------------------------------------------

def make_duplicate_detector_node(
    db: Optional[AsyncSession] = None,
    similarity_threshold: float = 0.75,
) -> Callable[[ComplaintState], Any]:
    """
    Factory creating a LangGraph `duplicate_detector` node configured with a DB session
    and custom similarity threshold.

    Parameters
    ----------
    db : AsyncSession
        Active database session to query candidate complaints. If None, operates
        in offline mock mode (returns empty duplicates or matches in-memory list).
    similarity_threshold : float
        Threshold score (0.0 - 1.0) above which a candidate is flagged as a duplicate.

    Returns
    -------
    Async node callable compatible with LangGraph.
    """

    async def duplicate_detector_node(state: ComplaintState) -> ComplaintState:
        extracted = state.get("extracted_fields", {})
        current_id = state.get("complaint_id")

        product_name = extracted.get("product_name") or ""
        batch_no = extracted.get("batch_no") or ""
        description = extracted.get("description") or state.get("raw_text", "")

        duplicates: List[Dict[str, Any]] = []

        # If no DB session provided, return empty list (or pre-set candidates if testing)
        if db is None:
            logger.info("duplicate_detector_node: No DB session supplied; skipping DB check.")
            state["possible_duplicates"] = duplicates
            return state

        if not product_name and not batch_no:
            logger.info("duplicate_detector_node: Neither product_name nor batch_no present.")
            state["possible_duplicates"] = duplicates
            return state

        try:
            # -------------------------------------------------------------------
            # Step 1: Query candidates with matching batch_no or product_name
            # -------------------------------------------------------------------
            conditions = []
            if batch_no and batch_no.lower() not in ("unknown", "n/a", "none"):
                conditions.append(Complaint.batch_no == batch_no.upper().strip())
            if product_name:
                conditions.append(Complaint.product_name.ilike(f"%{product_name.strip()}%"))

            stmt = select(Complaint).where(or_(*conditions))
            if current_id:
                stmt = stmt.where(Complaint.id != current_id)

            result = await db.scalars(stmt)
            candidates = result.all()

            logger.info(
                "duplicate_detector_node: Found %d candidate complaints in DB.", len(candidates)
            )

            # -------------------------------------------------------------------
            # Step 2 & 3: Compute similarity & filter above threshold
            # -------------------------------------------------------------------
            for cand in candidates:
                # 1. Exact batch_no match gives a baseline priority score
                batch_match = (
                    batch_no
                    and cand.batch_no
                    and cand.batch_no.upper() == batch_no.upper().strip()
                )

                # Compute TF-IDF text similarity on description
                score = compute_similarity(description, cand.description or "")

                # Boost score slightly if batch_no is an exact match
                if batch_match:
                    score = max(score, 0.80)  # Same batch = high duplicate probability

                if score >= similarity_threshold:
                    duplicates.append({
                        "complaint_id": cand.id,
                        "complaint_number": cand.complaint_number,
                        "product_name": cand.product_name,
                        "batch_no": cand.batch_no,
                        "similarity_score": round(float(score), 4),
                        "match_type": "exact_batch" if batch_match else "text_similarity",
                    })

            # Sort duplicates by similarity score DESC
            duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)

            logger.info(
                "duplicate_detector_node: Identified %d duplicates above threshold %.2f.",
                len(duplicates),
                similarity_threshold,
            )

        except Exception as exc:
            logger.error("duplicate_detector_node DB error: %s", exc)

        state["possible_duplicates"] = duplicates
        return state

    return duplicate_detector_node
