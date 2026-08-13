"""
app/schemas/copilot.py
-----------------------
Pydantic schemas for the AI Copilot Chat & Upload endpoints.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class CopilotMessageRequest(BaseModel):
    session_id: str = Field(..., description="Unique chat session / thread identifier")
    message: str = Field(..., min_length=1, description="User's text message or correction statement")
    complaint_id: Optional[int] = Field(None, description="Active complaint ID if correcting an existing record")


class CopilotNewComplaintResponse(BaseModel):
    complaint_id: int
    complaint_number: str
    extracted_fields: Dict[str, Any]
    severity: Optional[str] = None
    suggested_next_action: Optional[str] = None
    initial_risk_assessment: Optional[str] = None
    reply_text: str


class CopilotCorrectionResponse(BaseModel):
    complaint_id: int
    updated_fields: Dict[str, Any]
    reply_text: str
