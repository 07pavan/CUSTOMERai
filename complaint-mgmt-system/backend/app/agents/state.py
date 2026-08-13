"""
app/agents/state.py
-------------------
LangGraph State Schema for the Pharmaceutical Complaint Triage Pipeline.

Defines `ComplaintState` as a TypedDict that flows through the LangGraph
nodes:
  1. Intake & Extract Fields (Gemma 9B)
  2. Completeness Check (Gemma 9B / Python logic)
  3. Risk Assessment (Llama 70B)
  4. Duplicate Check (Llama 70B / Vector / Exact match)
  5. Root Cause & CAPA Generation (Llama 70B)
  6. Final Summary Synthesis (Llama 70B)
"""

from typing import Any, Dict, List, Optional, TypedDict


class ComplaintState(TypedDict, total=False):
    """
    State object passed between LangGraph nodes during complaint processing.

    Fields
    ------
    complaint_id         : Primary key ID of the complaint being assessed (if saved in DB).
    raw_text             : Combined raw text from intake description and extracted attachments.
    extracted_fields     : Dict of extracted structured entities (product_name, batch_no, etc.).
    completeness_flags   : Dict or list detailing missing/ambiguous required fields.
    risk_level           : Assigned risk level: 'critical' | 'major' | 'minor'.
    risk_rationale       : Regulatory / medical justification for the assigned risk level.
    possible_duplicates  : List of potential duplicate complaints identified.
    root_cause_suggestion: Hypothesized root cause analysis.
    capa_suggestion      : Recommended Corrective & Preventive Actions.
    summary              : Executive summary of the triage assessment.
    error                : Optional error message if any node failed during processing.
    """

    complaint_id: Optional[int]
    raw_text: str
    extracted_fields: Dict[str, Any]
    completeness_flags: Dict[str, Any]
    risk_level: Optional[str]
    risk_rationale: Optional[str]
    possible_duplicates: List[Dict[str, Any]]
    root_cause_suggestion: Optional[str]
    capa_suggestion: Optional[str]
    summary: Optional[str]
    error: Optional[str]
