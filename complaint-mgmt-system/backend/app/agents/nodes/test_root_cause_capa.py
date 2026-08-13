"""
app/agents/nodes/test_root_cause_capa.py
-----------------------------------------
Standalone test script for `root_cause_recommender_node` and `capa_recommender_node`.

Runs intake parsing, risk classification, root cause analysis, and CAPA recommendation
in sequence for 2 sample documents:
  1. complaint_03_packaging_defect.pdf (Blister Packaging Defect)
  2. complaint_04_particulate_matter.pdf (Sterile Injectable Particulate Matter)

Usage:
  cd backend
  python -m app.agents.nodes.test_root_cause_capa
"""

import asyncio
from pathlib import Path

from app.agents.nodes.capa_recommender import capa_recommender_node
from app.agents.nodes.intake_parser import intake_parser_node
from app.agents.nodes.risk_classifier import risk_classifier_node
from app.agents.nodes.root_cause_recommender import root_cause_recommender_node
from app.agents.state import ComplaintState
from app.core.config import settings
from app.core.extraction import extract_text_from_pdf

def _find_sample_dir() -> Path:
    curr = Path(__file__).resolve().parent
    for _ in range(6):
        candidate = curr / "sample_data"
        if candidate.exists() and candidate.is_dir():
            return candidate
        curr = curr.parent
    raise FileNotFoundError("Could not locate sample_data directory.")

SAMPLE_DIR = _find_sample_dir()


async def main():
    print("============================================================")
    print("STANDALONE TEST: Root Cause & CAPA Recommender Nodes")
    print("============================================================")
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        print(" [NOTE] GROQ_API_KEY unconfigured — using deterministic 5M/CAPA fallback.\n")
    else:
        print(" [NOTE] GROQ_API_KEY active — running live Llama 3.3 70B nodes.\n")

    files = [
        "complaint_03_packaging_defect.pdf",
        "complaint_04_particulate_matter.pdf",
    ]

    for filename in files:
        filepath = SAMPLE_DIR / filename
        if not filepath.exists():
            continue

        raw_text = extract_text_from_pdf(filepath)
        state: ComplaintState = {"raw_text": raw_text}

        # Step 1: Parse
        state = await intake_parser_node(state)
        # Step 2: Risk Classify
        state = await risk_classifier_node(state)
        # Step 3: Root Cause Recommendation
        state = await root_cause_recommender_node(state)
        # Step 4: CAPA Recommendation
        state = await capa_recommender_node(state)

        extracted = state.get("extracted_fields", {})
        product = extracted.get("product_name") or "Unspecified Product"
        risk = state.get("risk_level", "unknown").upper()
        rca = state.get("root_cause_suggestion", "")
        capa = state.get("capa_suggestion", "")

        print(f"--- DOCUMENT: {filename} ---")
        print(f"Product: {product}")
        print(f"Risk   : [{risk}]")
        print("\nROOT CAUSE HYPOTHESES (5M):")
        print(rca)
        print("\nDRAFT CAPA RECOMMENDATION:")
        print(capa)
        print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
