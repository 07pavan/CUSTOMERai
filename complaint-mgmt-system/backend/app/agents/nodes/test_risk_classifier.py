"""
app/agents/nodes/test_risk_classifier.py
------------------------------------------
Standalone test script for `risk_classifier_node`.

Runs `intake_parser_node` followed by `risk_classifier_node` against all 6 sample files
in `sample_data/` to verify pharmaceutical risk level classification:

  1. complaint_01_discoloration.eml
  2. complaint_02_chipped_tablets.txt
  3. complaint_03_packaging_defect.pdf
  4. complaint_04_particulate_matter.pdf
  5. complaint_05_dosage_mixup.txt
  6. complaint_06_counterfeit_packaging.txt

Usage:
  cd backend
  python -m app.agents.nodes.test_risk_classifier
"""

import asyncio
import json
from pathlib import Path

from app.agents.nodes.intake_parser import intake_parser_node
from app.agents.nodes.risk_classifier import risk_classifier_node
from app.agents.state import ComplaintState
from app.core.config import settings
from app.core.extraction import extract_text_from_eml, extract_text_from_pdf, extract_text_from_txt

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
    print("STANDALONE TEST: risk_classifier_node (Llama 3.3 70B)")
    print("============================================================")
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        print(" [NOTE] GROQ_API_KEY unconfigured — using deterministic GXP rule fallback.\n")
    else:
        print(" [NOTE] GROQ_API_KEY active — running live classification against Llama 3.3 70B.\n")

    files = [
        ("complaint_01_discoloration.eml",        extract_text_from_eml),
        ("complaint_02_chipped_tablets.txt",       extract_text_from_txt),
        ("complaint_03_packaging_defect.pdf",     extract_text_from_pdf),
        ("complaint_04_particulate_matter.pdf",   extract_text_from_pdf),
        ("complaint_05_dosage_mixup.txt",          extract_text_from_txt),
        ("complaint_06_counterfeit_packaging.txt", extract_text_from_txt),
    ]

    for filename, extract_fn in files:
        filepath = SAMPLE_DIR / filename
        if not filepath.exists():
            print(f"Skipping {filename} — file not found.")
            continue

        raw_text = extract_fn(filepath)
        state: ComplaintState = {"raw_text": raw_text}

        # Step 1: Parse fields
        state = await intake_parser_node(state)

        # Step 2: Classify risk
        result = await risk_classifier_node(state)

        extracted = result.get("extracted_fields", {})
        product = extracted.get("product_name") or "Unspecified Product"
        category = extracted.get("category") or "quality"
        risk_level = result.get("risk_level", "unknown").upper()
        rationale = result.get("risk_rationale", "")

        print(f"--- DOCUMENT: {filename} ---")
        print(f"Product  : {product}")
        print(f"Category : {category}")
        print(f"Risk     : [{risk_level}]")
        print(f"Rationale: {rationale}")
        print("-" * 60 + "\n")

    print("============================================================")


if __name__ == "__main__":
    asyncio.run(main())
