import asyncio
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.base import Base
from app.api.copilot import process_copilot_message, upload_copilot_document
from app.schemas.copilot import CopilotMessageRequest
from app.api.assessments import run_assessment
from app.agents.nodes.intake_parser import intake_parser_node
from app.agents.nodes.risk_classifier import risk_classifier_node
from fastapi import UploadFile

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def run_verification():
    print("=" * 80)
    print("1. GROQ KEY CHECK")
    print("=" * 80)
    print(f"GROQ_API_KEY set: {bool(settings.GROQ_API_KEY)}")
    if settings.GROQ_API_KEY:
        print(f"Key preview: {settings.GROQ_API_KEY[:8]}...{settings.GROQ_API_KEY[-6:]}")
    
    test_state = {"raw_text": "Apollo Pharmacy reported 12 discolored capsules in Amoxicillin Capsules 500mg. Batch AMX240602."}
    res = await intake_parser_node(test_state)
    print("\n[Intake Parser Output]:")
    print(json.dumps(res.get("extracted_fields"), indent=2))
    
    await init_db()
    
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 80)
        print("2. END-TO-END NEW COMPLAINT")
        print("=" * 80)
        text_1 = "Apollo Pharmacy reported 12 discolored capsules in Amoxicillin Capsules 500mg. Batch number AMX240602. Manufacturing date March 2026. Expiry date February 2028. Please log this complaint."
        req_1 = CopilotMessageRequest(session_id="verification_sess", message=text_1, complaint_id=None)
        res_1 = await process_copilot_message(req_1, db=db, actor="system.tester")
        res_1_json = res_1 if isinstance(res_1, dict) else res_1.model_dump()
        print("[Raw Response JSON]:")
        print(json.dumps(json.loads(res_1.model_dump_json()), indent=2))
        
        cmp_id = res_1.complaint_id
        
        print("\n" + "=" * 80)
        print("3. END-TO-END CORRECTION")
        print("=" * 80)
        text_2 = "ah sorry the batch number is BMX240602 and affected quantity is 48 capsules"
        req_2 = CopilotMessageRequest(session_id="verification_sess", message=text_2, complaint_id=cmp_id)
        res_2 = await process_copilot_message(req_2, db=db, actor="system.tester")
        print("[Raw Response JSON]:")
        print(json.dumps(json.loads(res_2.model_dump_json()), indent=2))
        
        print("\n" + "=" * 80)
        print("4. FULL PIPELINE (ALL 7 NODES)")
        print("=" * 80)
        res_4 = await run_assessment(complaint_id=cmp_id, db=db, actor="system.tester")
        print("[Full 7-Node Assessment Response JSON]:")
        print(json.dumps(json.loads(res_4.model_dump_json()), indent=2))
        
        print("\n" + "=" * 80)
        print("5. FILE UPLOAD PATH")
        print("=" * 80)
        pdf_path = os.path.join("..", "sample_data", "complaint_04_particulate_matter.pdf")
        if not os.path.exists(pdf_path):
            pdf_path = os.path.join("sample_data", "complaint_04_particulate_matter.pdf")
            
        with open(pdf_path, "rb") as f:
            upload_file = UploadFile(filename="complaint_04_particulate_matter.pdf", file=f)
            res_5 = await upload_copilot_document(file=upload_file, session_id="verification_sess_file", complaint_id=None, db=db, actor="system.tester")
            print("[File Upload Raw Response JSON]:")
            print(json.dumps(json.loads(res_5.model_dump_json()), indent=2))

if __name__ == "__main__":
    asyncio.run(run_verification())
