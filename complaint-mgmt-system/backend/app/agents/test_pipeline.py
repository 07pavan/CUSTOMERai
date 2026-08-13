"""
app/agents/test_pipeline.py
----------------------------
End-to-End Integration Test for the LangGraph Complaint Processing Pipeline.

Runs `run_complaint_pipeline` against sample documents in `sample_data/` and
pretty-prints every field of the final state dictionary.

Usage:
  cd backend
  python -m app.agents.test_pipeline
"""

import asyncio
import json
from pathlib import Path

from app.agents.graph import run_complaint_pipeline
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
    print("==========================================================================")
    print("END-TO-END LANGGRAPH PIPELINE INTEGRATION TEST")
    print("==========================================================================")
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        print(" [NOTE] GROQ_API_KEY unconfigured — graph will execute via GXP fallback rules.")
        print(" [NOTE] Supply GROQ_API_KEY in backend/.env for live multi-model execution.\n")
    else:
        print(" [NOTE] GROQ_API_KEY detected — executing full multi-model LangGraph graph.\n")

    sample_file = SAMPLE_DIR / "complaint_03_packaging_defect.pdf"
    print(f"Loading sample document: {sample_file.name}")

    raw_text = extract_text_from_pdf(sample_file)
    print(f"Extracted Raw Text Snippet ({len(raw_text)} chars):\n{raw_text[:250]}...\n")

    print("Running `run_complaint_pipeline` through 7-node LangGraph graph...")
    print("  [intake_parser -> completeness_checker -> risk_classifier -> duplicate_detector -> root_cause_recommender -> capa_recommender -> summary_generator]\n")

    final_state = await run_complaint_pipeline(raw_text=raw_text)

    print("==========================================================================")
    print("FINAL LANGGRAPH STATE DICTIONARY OUTPUT")
    print("==========================================================================")

    print("\n1. EXTRACTED FIELDS (state['extracted_fields']):")
    print(json.dumps(final_state.get("extracted_fields"), indent=2))

    print("\n2. COMPLETENESS FLAGS (state['completeness_flags']):")
    print(json.dumps(final_state.get("completeness_flags"), indent=2))

    print("\n3. RISK CLASSIFICATION:")
    print(f"   Level    : [{final_state.get('risk_level', '').upper()}]")
    print(f"   Rationale: {final_state.get('risk_rationale')}")

    print("\n4. POSSIBLE DUPLICATES (state['possible_duplicates']):")
    print(json.dumps(final_state.get("possible_duplicates"), indent=2))

    print("\n5. ROOT CAUSE SUGGESTION (state['root_cause_suggestion']):")
    print(final_state.get("root_cause_suggestion"))

    print("\n6. CAPA SUGGESTION (state['capa_suggestion']):")
    print(final_state.get("capa_suggestion"))

    print("\n7. EXECUTIVE SUMMARY (state['summary']):")
    print(final_state.get("summary"))

    print("\n==========================================================================")
    print("END-TO-END PIPELINE TEST COMPLETED SUCCESSFULLY")
    print("==========================================================================")


if __name__ == "__main__":
    asyncio.run(main())
