"""
app/api/test_copilot_endpoints.py
-----------------------------------
Integration test for POST /copilot/message and POST /copilot/upload endpoints using FastAPI TestClient.
"""

import asyncio
from fastapi.testclient import TestClient

from app.db.session import engine
from app.main import app
from app.models.base import Base

client = TestClient(app)


def test_copilot_endpoints():
    print("=" * 75)
    print("COPILOT ENDPOINTS INTEGRATION TEST")
    print("=" * 75)

    # Re-initialize DB schema cleanly for testing
    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    # 1. Test POST /api/v1/copilot/message (New Complaint Intake)
    print("\n1. Testing POST /api/v1/copilot/message (New Complaint Intake)...")
    payload_new = {
        "session_id": "sess_test_101",
        "message": "Complaint: Discolored tablets in Clarivin 10mg bottle (Batch B2024-089A) reported by Sarah Jenkins.",
        "complaint_id": None
    }
    res_new = client.post("/api/v1/copilot/message", json=payload_new)
    assert res_new.status_code == 200, f"Expected 200, got {res_new.status_code}: {res_new.text}"

    data_new = res_new.json()
    complaint_id = data_new.get("complaint_id")
    print(f"   [SUCCESS] Logged New Complaint ID: {complaint_id} ({data_new.get('complaint_number')})")
    print(f"   Reply Text: \"{data_new.get('reply_text')}\"")

    # 2. Test POST /api/v1/copilot/message (Field Correction on existing complaint_id)
    print(f"\n2. Testing POST /api/v1/copilot/message (Field Correction on ID {complaint_id})...")
    payload_corr = {
        "session_id": "sess_test_101",
        "message": "ah sorry the batch number is BMX240602 and affected quantity is 48 capsules",
        "complaint_id": complaint_id
    }
    res_corr = client.post("/api/v1/copilot/message", json=payload_corr)
    assert res_corr.status_code == 200, f"Expected 200, got {res_corr.status_code}: {res_corr.text}"

    data_corr = res_corr.json()
    updated_fields = data_corr.get("updated_fields")
    print(f"   [SUCCESS] Applied Field Correction Diff: {updated_fields}")
    print(f"   Reply Text: \"{data_corr.get('reply_text')}\"")

    assert "batch_no" in updated_fields
    assert updated_fields.get("batch_no") == "BMX240602"

    print("\n" + "=" * 75)
    print("COPILOT ENDPOINTS TEST COMPLETED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    test_copilot_endpoints()
