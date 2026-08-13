"""
app/agents/nodes/test_intake_parser.py
---------------------------------------
Standalone test script for `intake_parser_node`.

Runs the intake_parser node against sample files from `sample_data/`:
  1. complaint_01_discoloration.eml (Email - Complete)
  2. complaint_02_chipped_tablets.txt (Plain text - Missing batch #)

Usage:
  cd backend
  python -m app.agents.nodes.test_intake_parser
"""

import asyncio
import json
from pathlib import Path

from app.agents.nodes.intake_parser import intake_parser_node
from app.agents.state import ComplaintState
from app.core.extraction import extract_text_from_pdf

# Robustly find sample_data directory upwards from current file
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
    print("STANDALONE TEST: intake_parser_node (Gemma 2 9B IT)")
    print("============================================================")
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        print(" [NOTE] GROQ_API_KEY is unconfigured in .env.")
        print(" [NOTE] Node will run error-handling fallback mode.")
        print(" [NOTE] Set GROQ_API_KEY=gsk_... in .env for live Groq extraction.\n")
    else:
        print(" [NOTE] GROQ_API_KEY detected — running live LLM extraction against Groq API.\n")

    # --- Test Case 1: Email complaint (Complete) ---
    file1 = SAMPLE_DIR / "complaint_01_discoloration.eml"
    print(f"--- TEST CASE 1: {file1.name} ---")
    raw_text_1 = file1.read_text(encoding="utf-8")
    print(f"Raw Text Sample:\n{raw_text_1[:220]}...\n")

    state1: ComplaintState = {"raw_text": raw_text_1}
    result1 = await intake_parser_node(state1)

    print("Parsed Extracted Fields:")
    print(json.dumps(result1.get("extracted_fields"), indent=2))
    print("\n------------------------------------------------------------\n")

    # --- Test Case 2: Plain text complaint (Missing Lot/Batch #) ---
    file2 = SAMPLE_DIR / "complaint_02_chipped_tablets.txt"
    print(f"--- TEST CASE 2: {file2.name} (Should have null batch_no) ---")
    raw_text_2 = file2.read_text(encoding="utf-8")
    print(f"Raw Text Sample:\n{raw_text_2[:220]}...\n")

    state2: ComplaintState = {"raw_text": raw_text_2}
    result2 = await intake_parser_node(state2)

    print("Parsed Extracted Fields:")
    print(json.dumps(result2.get("extracted_fields"), indent=2))
    print("\n------------------------------------------------------------\n")

    # --- Test Case 3: PDF Document (Extracted via pdfplumber) ---
    file3 = SAMPLE_DIR / "complaint_03_packaging_defect.pdf"
    print(f"--- TEST CASE 3: {file3.name} (PDF Document) ---")
    raw_text_3 = extract_text_from_pdf(file3)
    print(f"Raw Text Sample:\n{raw_text_3[:220]}...\n")

    state3: ComplaintState = {"raw_text": raw_text_3}
    result3 = await intake_parser_node(state3)

    print("Parsed Extracted Fields:")
    print(json.dumps(result3.get("extracted_fields"), indent=2))
    print("\n============================================================")


if __name__ == "__main__":
    asyncio.run(main())
