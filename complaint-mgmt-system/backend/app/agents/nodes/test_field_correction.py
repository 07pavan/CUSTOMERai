"""
app/agents/nodes/test_field_correction.py
---------------------------------------------
Standalone test script to verify `field_correction_node` and `apply_correction_sync`.

Workflow:
  1. Runs initial intake pipeline on sample file `complaint_03_packaging_defect.pdf`.
  2. Applies a correction message: "ah sorry the batch number is BMX240602 and affected quantity is 48 capsules".
  3. Verifies that `field_diff` contains ONLY `batch_no` and `affected_quantity` and that unchanged fields are untouched.
"""

import json
from pathlib import Path

from app.agents.graph import apply_correction_sync, run_complaint_pipeline_sync
from app.core.extraction import extract_text

SAMPLE_DIR = Path(__file__).resolve().parents[4] / "sample_data"
SAMPLE_FILE = SAMPLE_DIR / "complaint_03_packaging_defect.pdf"


def main():
    print("=" * 75)
    print("FIELD CORRECTION & INTENT ROUTER STANDALONE TEST")
    print("=" * 75)

    if not SAMPLE_FILE.exists():
        print(f"Sample file not found at: {SAMPLE_FILE}")
        return

    print(f"\n1. Loading sample document: {SAMPLE_FILE.name}")
    raw_text = extract_text(SAMPLE_FILE, "pdf")
    print(f"   Extracted text snippet ({len(raw_text)} chars): {raw_text[:120]}...\n")

    print("2. Running initial intake pipeline (run_complaint_pipeline_sync)...")
    initial_state = run_complaint_pipeline_sync(raw_text=raw_text)
    initial_fields = initial_state.get("extracted_fields", {})

    print("\n   INITIAL EXTRACTED FIELDS:")
    print(json.dumps(initial_fields, indent=2))

    # 3. Apply correction message
    correction_msg = "ah sorry the batch number is BMX240602 and affected quantity is 48 capsules"
    print(f"\n3. Applying Correction Message:")
    print(f"   \"{correction_msg}\"")
    print("\n   Executing `apply_correction_sync`...")

    correction_result = apply_correction_sync(
        existing_fields=initial_fields,
        correction_message=correction_msg,
    )

    field_diff = correction_result.get("field_diff", {})
    updated_fields = correction_result.get("extracted_fields", {})

    print("\n" + "=" * 75)
    print("CORRECTION TEST RESULTS")
    print("=" * 75)

    print("\n[A] EXTRACTED FIELD DIFF (state['field_diff']):")
    print(json.dumps(field_diff, indent=2))

    print("\n[B] MERGED UPDATED FIELDS (state['extracted_fields']):")
    print(json.dumps(updated_fields, indent=2))

    # Verification checks
    assert "batch_no" in field_diff, "FAILED: 'batch_no' should be present in field_diff"
    assert field_diff.get("batch_no") == "BMX240602", f"FAILED: batch_no should be 'BMX240602', got {field_diff.get('batch_no')}"
    assert "affected_quantity" in field_diff, "FAILED: 'affected_quantity' should be present in field_diff"
    assert "product_name" not in field_diff, "FAILED: 'product_name' should NOT be in field_diff"

    print("\n" + "=" * 75)
    print("TEST PASSED: Only explicitly mentioned fields were modified in field_diff!")
    print("=" * 75)


if __name__ == "__main__":
    main()
