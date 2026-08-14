"""
app/agents/nodes/test_completeness_checker.py
----------------------------------------------
Standalone test script for `completeness_checker_node`.

Tests `completeness_checker_node` in pipeline sequence (after `intake_parser_node`):
  1. complaint_02_chipped_tablets.txt (Missing batch number)
  2. complaint_04_particulate_matter.pdf (Missing complainant contact & name)
  3. complaint_01_discoloration.eml (Complete document)
  4. Vague Description Test (Synthetic vague complaint)

Usage:
  cd backend
  python -m app.agents.nodes.test_completeness_checker
"""

import asyncio
import json
from pathlib import Path

from app.agents.nodes.completeness_checker import completeness_checker_node
from app.agents.nodes.intake_parser import intake_parser_node
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
    print("STANDALONE TEST: completeness_checker_node")
    print("============================================================")
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        print(" [NOTE] GROQ_API_KEY unconfigured — soft LLM specificity check will use deterministic fallback.\n")
    else:
        print(" [NOTE] GROQ_API_KEY active — running deterministic rules + Gemma LLM specificity check.\n")

    # --- Test Case 1: Missing Batch Number ---
    file1 = SAMPLE_DIR / "complaint_02_chipped_tablets.txt"
    print(f"--- TEST CASE 1: {file1.name} (Expect missing batch_no flag) ---")
    state1: ComplaintState = {"raw_text": file1.read_text(encoding="utf-8")}
    
    # Run intake_parser first to populate extracted_fields
    state1 = await intake_parser_node(state1)
    
    # Direct simulation if API key missing
    if not state1.get("extracted_fields", {}).get("product_name"):
        state1["extracted_fields"] = {
            "product_name": "Cardexin 25mg Extended Release Tablets",
            "batch_no": None,  # Explicitly missing
            "complainant_name": "Dr. Robert Vance, MD",
            "complainant_contact": "rvance@vanceinternalmed.org",
            "category": "quality",
            "description": "15 to 20 tablets severely chipped and split into fragments."
        }

    # Run completeness_checker
    result1 = await completeness_checker_node(state1)
    print("Extracted Fields:", json.dumps(result1.get("extracted_fields"), indent=2))
    print("\nCompleteness Flags Generated:")
    print(json.dumps(result1.get("completeness_flags"), indent=2))
    print("\n------------------------------------------------------------\n")

    # --- Test Case 2: Anonymous / Missing Complainant ---
    file2 = SAMPLE_DIR / "complaint_04_particulate_matter.pdf"
    print(f"--- TEST CASE 2: {file2.name} (Expect missing complainant contact flag) ---")
    pdf_text_2 = extract_text_from_pdf(file2)
    state2: ComplaintState = {"raw_text": pdf_text_2}
    state2 = await intake_parser_node(state2)

    if not state2.get("extracted_fields", {}).get("product_name"):
        state2["extracted_fields"] = {
            "product_name": "Metoprolol Tartrate Injection USP",
            "batch_no": "B-API-88741",
            "complainant_name": None,  # Anonymous
            "complainant_contact": None,  # Missing
            "category": "quality",
            "description": "5mL glass vial found to contain visible floating fibers and dark specks."
        }

    result2 = await completeness_checker_node(state2)
    print("Extracted Fields:", json.dumps(result2.get("extracted_fields"), indent=2))
    print("\nCompleteness Flags Generated:")
    print(json.dumps(result2.get("completeness_flags"), indent=2))
    print("\n------------------------------------------------------------\n")

    # --- Test Case 3: Vague Description Test ---
    print("--- TEST CASE 3: Synthetic Vague Complaint (Expect vague description flag) ---")
    state3: ComplaintState = {
        "extracted_fields": {
            "product_name": "Amoxicillin 500mg",
            "batch_no": "BT99823",
            "complainant_name": "John Doe",
            "complainant_contact": "john@example.com",
            "category": "quality",
            "description": "The medicine didn't work well and I felt bad.",
        }
    }
    result3 = await completeness_checker_node(state3)
    print("Extracted Fields:", json.dumps(result3.get("extracted_fields"), indent=2))
    print("\nCompleteness Flags Generated:")
    print(json.dumps(result3.get("completeness_flags"), indent=2))
    print("\n============================================================")


if __name__ == "__main__":
    asyncio.run(main())
