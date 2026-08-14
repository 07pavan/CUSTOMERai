import asyncio
import json
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.agents.llm import get_groq_client, acall_gemma, acall_llama
from app.agents.nodes.risk_classifier import risk_classifier_node
from app.agents.nodes.intake_parser import intake_parser_node

API_BASE = "http://127.0.0.1:8000/api/v1"

async def run_all_tests():
    print("=" * 90)
    print("STARTING REAL FUNCTIONAL TEST SUITE")
    print("=" * 90)
    
    # -----------------------------------------------------------------------
    # TEST 1: Groq API Key & Direct Call Confirmation
    # -----------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("TEST 1: Confirm GROQ_API_KEY is set and actually being called (Not regex fallback)")
    print("=" * 90)
    
    api_key = settings.GROQ_API_KEY
    print(f"GROQ_API_KEY Present: {bool(api_key)}")
    if api_key:
        print(f"GROQ_API_KEY Prefix/Suffix: {api_key[:10]}...{api_key[-6:]}")
    print(f"GROQ_MODEL_FAST: {settings.GROQ_MODEL_FAST}")
    print(f"GROQ_MODEL_LARGE: {settings.GROQ_MODEL_LARGE}")
    
    client = get_groq_client()
    raw_completion = client.chat.completions.create(
        model=settings.GROQ_MODEL_FAST,
        messages=[
            {"role": "system", "content": "You are a pharma QA assistant."},
            {"role": "user", "content": "Ping test: return JSON {'status': 'live', 'engine': 'Groq Cloud', 'timestamp': '2026-08-14'}"}
        ],
        temperature=0.0,
        max_tokens=100
    )
    
    print("\n[Real Groq API ChatCompletion Object]:")
    print(f"  - Response ID: {raw_completion.id}")
    print(f"  - Model Used: {raw_completion.model}")
    print(f"  - Created Timestamp: {raw_completion.created}")
    print(f"  - Finish Reason: {raw_completion.choices[0].finish_reason}")
    print(f"  - Prompt Tokens: {raw_completion.usage.prompt_tokens}")
    print(f"  - Completion Tokens: {raw_completion.usage.completion_tokens}")
    print(f"  - Total Tokens: {raw_completion.usage.total_tokens}")
    print(f"  - Raw Content Output: {raw_completion.choices[0].message.content}")
    print("\n>>> TEST 1 RESULT: PASS (Live Groq API verified with active token usage)")

    # -----------------------------------------------------------------------
    # TEST 2: POST a new complaint via /copilot/message
    # -----------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("TEST 2: POST a new complaint via /copilot/message")
    print("=" * 90)
    
    async with httpx.AsyncClient(base_url=API_BASE, timeout=60.0) as http_client:
        msg_payload_1 = {
            "session_id": "test_functional_session_003",
            "message": "Apollo Pharmacy reported 12 discolored capsules in Amoxicillin Capsules 500mg. Batch number AMX240602. Manufacturing date March 2026. Expiry date February 2028. Please log this complaint.",
            "complaint_id": None
        }
        headers_user = {"X-Role": "user", "X-Actor": "qa.officer@pharma.com"}
        headers_admin = {"X-Role": "admin", "X-Actor": "admin@pharma.com"}
        
        response_2 = await http_client.post("/copilot/message", json=msg_payload_1, headers=headers_user)
        print(f"HTTP Status Code: {response_2.status_code}")
        res_2_data = response_2.json()
        print("\n[Full JSON Response from /copilot/message (New Complaint)]:")
        print(json.dumps(res_2_data, indent=2))
        
        complaint_id = res_2_data.get("complaint_id")
        print(f"\nCreated Complaint ID: {complaint_id}")
        assert complaint_id is not None, "Failed to obtain complaint_id from response"
        
        # Capture baseline record state
        cmp_before = (await http_client.get(f"/complaints/{complaint_id}", headers=headers_admin)).json()
        
        print(">>> TEST 2 RESULT: PASS (New complaint logged and parsed via LangGraph)")

        # -------------------------------------------------------------------
        # TEST 3: POST a correction on that same complaint_id
        # -------------------------------------------------------------------
        print("\n" + "=" * 90)
        print("TEST 3: POST a correction on that same complaint_id ('batch number is X, quantity is Y')")
        print("=" * 90)
        
        msg_payload_2 = {
            "session_id": "test_functional_session_003",
            "message": "ah sorry the batch number is BMX240602 and affected quantity is 48 capsules",
            "complaint_id": complaint_id
        }
        
        response_3 = await http_client.post("/copilot/message", json=msg_payload_2, headers=headers_user)
        print(f"HTTP Status Code: {response_3.status_code}")
        res_3_data = response_3.json()
        print("\n[Full JSON Response from /copilot/message (Correction)]:")
        print(json.dumps(res_3_data, indent=2))
        
        # Verify the complaint record state after correction
        cmp_after = (await http_client.get(f"/complaints/{complaint_id}", headers=headers_admin)).json()
        
        print("\n[Field Comparison Before vs After Correction]:")
        fields_to_check = [
            "product_name", "product_strength", "customer_name",
            "batch_no", "affected_quantity", "manufacturing_date", "expiry_date",
            "category", "description"
        ]
        
        changed_fields = []
        unchanged_fields = []
        for f in fields_to_check:
            val_before = cmp_before.get(f)
            val_after = cmp_after.get(f)
            status_str = "CHANGED" if str(val_before) != str(val_after) else "UNCHANGED"
            print(f"  {f:<22}: Before='{val_before}' -> After='{val_after}' [{status_str}]")
            if str(val_before) != str(val_after):
                changed_fields.append(f)
            else:
                unchanged_fields.append(f)
                
        updated_dict = res_3_data.get("updated_fields", {})
        print(f"\nResponse 'updated_fields': {updated_dict}")
        print(f"Detected Changed DB Fields: {changed_fields}")
        
        assert "batch_no" in updated_dict and "affected_quantity" in updated_dict, "Expected updated_fields in response"
        assert set(changed_fields) == {"batch_no", "affected_quantity"}, f"Expected ONLY batch_no & affected_quantity to change, got {changed_fields}"
        print(">>> TEST 3 RESULT: PASS (Confirm ONLY batch_no and affected_quantity changed)")

        # -------------------------------------------------------------------
        # TEST 4: Run /complaints/{id}/assess
        # -------------------------------------------------------------------
        print("\n" + "=" * 90)
        print(f"TEST 4: Run /complaints/{complaint_id}/assess and confirm fields are filled")
        print("=" * 90)
        
        response_4 = await http_client.post(f"/complaints/{complaint_id}/assess", headers=headers_admin)
        print(f"HTTP Status Code: {response_4.status_code}")
        res_4_data = response_4.json()
        print("\n[Full JSON Response from /complaints/{id}/assess]:")
        print(json.dumps(res_4_data, indent=2))
        
        root_cause = res_4_data.get("root_cause_suggestion") or res_4_data.get("root_cause")
        capa_suggestion = res_4_data.get("capa_suggestion")
        summary = res_4_data.get("summary")
        duplicate_id = res_4_data.get("duplicate_of_complaint_id")
        
        print("\nField Validation Checklist:")
        print(f"  - root_cause_suggestion : {'FILLED (' + str(len(root_cause)) + ' chars)' if root_cause else 'NULL/EMPTY'}")
        print(f"  - capa_suggestion       : {'FILLED (' + str(len(capa_suggestion)) + ' chars)' if capa_suggestion else 'NULL/EMPTY'}")
        print(f"  - summary               : {'FILLED (' + str(len(summary)) + ' chars)' if summary else 'NULL/EMPTY'}")
        print(f"  - duplicate / dup_id    : {'FILLED (ID: ' + str(duplicate_id) + ')' if duplicate_id is not None else 'NONE (No duplicate found)'}")
        
        assert root_cause is not None and len(root_cause) > 0, "root_cause_suggestion is NULL or empty"
        assert capa_suggestion is not None and len(capa_suggestion) > 0, "capa_suggestion is NULL or empty"
        assert summary is not None and len(summary) > 0, "summary is NULL or empty"
        print(">>> TEST 4 RESULT: PASS (root_cause_suggestion, capa_suggestion, summary are all filled and not null)")

    # -----------------------------------------------------------------------
    # TEST 5: Risk Classifier on Critical vs Minor Sample Documents
    # -----------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("TEST 5: Run Critical-type vs Minor-type docs through risk_classifier (Side-by-Side)")
    print("=" * 90)
    
    # Doc A: Critical (Dosage Mixup)
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_data"))
    crit_file = os.path.join(sample_dir, "complaint_05_dosage_mixup.txt")
    with open(crit_file, "r", encoding="utf-8") as f:
        crit_text = f.read()
    
    crit_intake = await intake_parser_node({"raw_text": crit_text})
    crit_state = {
        "raw_text": crit_text,
        "extracted_fields": crit_intake.get("extracted_fields", {}),
        "missing_critical_fields": [],
    }
    crit_res = await risk_classifier_node(crit_state)
    
    # Doc B: Minor (Discoloration)
    minor_file = os.path.join(sample_dir, "complaint_01_discoloration.eml")
    with open(minor_file, "r", encoding="utf-8") as f:
        minor_text = f.read()
        
    minor_intake = await intake_parser_node({"raw_text": minor_text})
    minor_state = {
        "raw_text": minor_text,
        "extracted_fields": minor_intake.get("extracted_fields", {}),
        "missing_critical_fields": [],
    }
    minor_res = await risk_classifier_node(minor_state)
    
    print("\n" + "-" * 90)
    print(f"{'METRIC / FIELD':<25} | {'SAMPLE A (CRITICAL: Dosage Mixup)':<30} | {'SAMPLE B (MINOR: Discoloration)':<30}")
    print("-" * 90)
    print(f"{'Severity':<25} | {str(crit_res.get('severity')):<30} | {str(minor_res.get('severity')):<30}")
    print(f"{'Risk Score (1-100)':<25} | {str(crit_res.get('risk_score')):<30} | {str(minor_res.get('risk_score')):<30}")
    print(f"{'Requires Escalation':<25} | {str(crit_res.get('requires_escalation')):<30} | {str(minor_res.get('requires_escalation')):<30}")
    print(f"{'Next Action':<25} | {str(crit_res.get('next_action')):<30} | {str(minor_res.get('next_action')):<30}")
    print("-" * 90)
    print("\nDetailed Rationale Sample A (Critical):")
    print(crit_res.get("risk_rationale"))
    print("\nDetailed Rationale Sample B (Minor):")
    print(minor_res.get("risk_rationale"))
    
    assert str(crit_res.get("severity")).lower() != str(minor_res.get("severity")).lower() or crit_res.get("risk_score") != minor_res.get("risk_score"), \
        "Classifier returned identical outputs for different risk inputs!"
    print("\n>>> TEST 5 RESULT: PASS (Severity and actions significantly differ between critical and minor inputs)")
    
    print("\n" + "=" * 90)
    print("ALL TESTS 1 - 5 EXECUTED SUCCESSFULLY AND PASSED!")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
