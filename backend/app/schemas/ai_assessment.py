"""
app/schemas/ai_assessment.py
-----------------------------
Pydantic schemas for AIAssessment (LangGraph agent output).

Notes
-----
* AIAssessmentCreate is used internally by the agent service — it is NOT a
  public API endpoint body. The API only exposes a trigger endpoint
  (POST /complaints/{id}/assess) which returns AIAssessmentResponse.

* completeness_flags is typed as list[CompletenessFlag] for strict validation
  on create, but stored as JSONB. The response type mirrors this.

* raw_llm_output is Any (dict) — we don't enforce its schema because LLM
  provider response formats can change between SDK versions.

* We include `model_name` in the create schema so we know which LLM produced
  each assessment — important when multiple models (gemma2-9b-it vs
  llama-3.3-70b-versatile) produce different outputs for the same complaint.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskLevel


class CompletenessFlag(BaseModel):
    """
    A single completeness issue identified by the AI agent.
    e.g. {"field": "batch_no", "issue": "not verifiable in product catalogue"}
    """
    field: str = Field(..., description="The complaint field that has an issue.")
    issue: str = Field(..., description="Description of why the field is missing or ambiguous.")


class AIAssessmentCreate(BaseModel):
    """
    Internal schema — populated by the LangGraph agent service after parsing
    the LLM output. Not exposed as a public request body.
    """
    # complaint_id injected by service layer — not in body.
    risk_level: RiskLevel
    risk_rationale: str
    completeness_flags: Optional[list[CompletenessFlag]] = None
    root_cause_suggestion: Optional[str] = None
    capa_suggestion: Optional[str] = None
    duplicate_of_complaint_id: Optional[int] = None
    summary: Optional[str] = None
    raw_llm_output: Optional[dict[str, Any]] = None
    model_name: Optional[str] = Field(
        None,
        description="LLM model used, e.g. 'gemma2-9b-it' or 'llama-3.3-70b-versatile'.",
    )


class AIAssessmentResponse(BaseModel):
    """Full assessment response — returned by GET /complaints/{id}/assessments."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    risk_level: RiskLevel
    risk_rationale: str
    completeness_flags: Optional[list[Any]]   # list[CompletenessFlag] at runtime
    root_cause_suggestion: Optional[str]
    capa_suggestion: Optional[str]
    duplicate_of_complaint_id: Optional[int]
    summary: Optional[str]
    # raw_llm_output excluded from default response — too verbose.
    # Expose via GET /complaints/{id}/assessments/{assessment_id}/raw if needed.
    created_at: datetime


class AIAssessmentTriggerResponse(BaseModel):
    """
    Response to POST /complaints/{id}/assess — confirms the assessment was
    queued or completed, depending on whether it runs sync or async.
    """
    queued: bool = Field(
        ...,
        description="True if assessment is running in background, False if completed inline.",
    )
    assessment_id: Optional[int] = None
    message: str = "Assessment triggered successfully."
