"""
app/agents/nodes/test_duplicate_detector.py
--------------------------------------------
Standalone test script for `duplicate_detector` node and `compute_similarity`.

Tests:
  1. TF-IDF Cosine Similarity calculation between matching vs distinct complaint descriptions.
  2. Factory pattern node execution with mock and database session inputs.

Usage:
  cd backend
  python -m app.agents.nodes.test_duplicate_detector
"""

import asyncio
import json
from app.agents.nodes.duplicate_detector import (
    compute_similarity,
    make_duplicate_detector_node,
)
from app.agents.state import ComplaintState


async def main():
    print("============================================================")
    print("STANDALONE TEST: duplicate_detector & compute_similarity")
    print("============================================================\n")

    # --- Test 1: TF-IDF Cosine Similarity Tests ---
    print("--- 1. TF-IDF COSINE SIMILARITY MATRIX ---")

    text_a = "15 to 20 tablets severely chipped and split into fragments inside 90 count bottle."
    text_b = "Bottle contained 15 tablets severely chipped and broken into pieces."
    text_c = "Foil pouch barrier has unsealed bottom margin and moisture exposure."

    score_ab = compute_similarity(text_a, text_b)
    score_ac = compute_similarity(text_a, text_c)

    print(f"Text A vs Text B (Near-Duplicate Descriptions):\n  Score: {score_ab:.4f}  (Expected >= 0.50)")
    print(f"Text A vs Text C (Unrelated Defects):\n  Score: {score_ac:.4f}  (Expected < 0.20)\n")

    assert score_ab > score_ac, "Near-duplicate score should be significantly higher than unrelated score."
    print("[OK] TF-IDF Cosine Similarity algorithm passed validation.\n")

    # --- Test 2: Node Factory Execution (Offline Mode) ---
    print("--- 2. NODE FACTORY & THREADING DEMONSTRATION ---")

    # Instantiating node with factory function
    threshold = 0.75
    detector_node = make_duplicate_detector_node(db=None, similarity_threshold=threshold)

    state: ComplaintState = {
        "extracted_fields": {
            "product_name": "Clarivin 10mg Tablets",
            "batch_no": "B2024-089A",
            "description": text_a,
        }
    }

    result_state = await detector_node(state)
    print("Executed Factory Node with threshold=0.75:")
    print("Possible Duplicates Output:", json.dumps(result_state.get("possible_duplicates"), indent=2))
    print("\n============================================================")


if __name__ == "__main__":
    asyncio.run(main())
