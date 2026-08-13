"""
app/agents/state.py
-------------------
LangGraph State Schema for the Pharmaceutical Complaint Triage Pipeline.
"""

from typing import Any, Dict, List, Optional, TypedDict


class ComplaintState(TypedDict, total=False):
    """
    State object passed between LangGraph nodes during complaint processing.

    Fields
    ------
    complaint_id           : Primary key ID of the complaint being assessed (if saved in DB).
    raw_text               : Combined raw text from intake description and extracted attachments.
    extracted_fields       : Dict of extracted structured entities (complaint_source, customer_name, etc.).
    completeness_flags     : Dict or list detailing missing/ambiguous required fields.
    severity               : Assigned risk severity: 'critical' | 'major' | 'minor' (or 'Critical'|'Major'|'Minor').
    suggested_next_action  : Short actionable recommendation phrase for QA triage.
    initial_risk_assessment: 1-2 sentence regulatory/medical justification.
    risk_level             : Alias for severity (for downstream compatibility).
    risk_rationale         : Alias for initial_risk_assessment.
    possible_duplicates    : List of potential duplicate complaints identified.
    root_cause_suggestion  : Hypothesized 5M root cause analysis.
    capa_suggestion        : Recommended Corrective & Preventive Actions.
    summary                : Executive summary of the triage assessment.
    error                  : Optional error message if any node failed during processing.
    """

    complaint_id: Optional[int]
    raw_text: str
    extracted_fields: Dict[str, Any]
    completeness_flags: Dict[str, Any]
    severity: Optional[str]
    suggested_next_action: Optional[str]
    initial_risk_assessment: Optional[str]
    risk_level: Optional[str]
    risk_rationale: Optional[str]
    possible_duplicates: List[Dict[str, Any]]
    root_cause_suggestion: Optional[str]
    capa_suggestion: Optional[str]
    summary: Optional[str]
    error: Optional[str]
