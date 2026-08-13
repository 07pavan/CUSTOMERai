"""
app/schemas/copilot.py
-----------------------
Pydantic schemas for the AI Copilot Chat & Upload endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text content")


class CopilotMessageRequest(BaseModel):
    session_id: str = Field(..., description="Unique chat session / thread identifier")
    message: str = Field(..., min_length=1, description="User's text message or correction statement")
    complaint_id: Optional[int] = Field(None, description="Active complaint ID if correcting an existing record")
    chat_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Last N turns of conversation for context. Each item has 'role' ('user'|'assistant') and 'content'.",
    )


class CopilotNewComplaintResponse(BaseModel):
    complaint_id: Optional[int] = None
    complaint_number: str = ""
    extracted_fields: Dict[str, Any] = {}
    severity: Optional[str] = None
    suggested_next_action: Optional[str] = None
    initial_risk_assessment: Optional[str] = None
    reply_text: str


class CopilotCorrectionResponse(BaseModel):
    complaint_id: Optional[int]
    updated_fields: Dict[str, Any]
    reply_text: str
    action: Optional[str] = None  # e.g. "submit" — tells the frontend to trigger form submission
