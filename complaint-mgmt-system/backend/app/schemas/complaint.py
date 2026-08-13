"""
app/schemas/complaint.py
-------------------------
Pydantic v2 request/response schemas for the Complaint resource.

Schema design philosophy
-------------------------
* We maintain separate Create / Update / Response schemas rather than
  a single all-purpose model. This lets us:
    - Keep server-generated fields (id, complaint_number, created_at, etc.)
    - out of the request body validation surface.
    - Make Update fields Optional without polluting the Create schema.
    - Version the API independently of the DB model.

* ComplaintResponse uses `model_config = ConfigDict(from_attributes=True)`
  (Pydantic v2 style, replaces `orm_mode = True`) to allow construction
  directly from SQLAlchemy ORM objects: `ComplaintResponse.model_validate(orm_obj)`.

* severity is Optional[Severity] in both Create and Response because it starts
  NULL and is populated asynchronously by the AI agent.

* complaint_number is excluded from ComplaintCreate — it's generated server-side.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import Category, Severity, SourceType, Status


# ======================================================================= #
# Request schemas                                                          #
# ======================================================================= #

class ComplaintCreate(BaseModel):
    """
    Body expected when a new complaint is submitted via POST /complaints.
    All user-supplied fields only — server generates: id, complaint_number,
    severity (async AI), status (defaults to 'new'), created_at, updated_at.
    """

    product_name: str = Field(..., min_length=1, max_length=255, examples=["Amoxicillin 500mg"])
    batch_no: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Batch/lot number. Use 'UNKNOWN' if not on hand.",
        examples=["BT20260401"],
    )
    complainant_name: str = Field(..., min_length=1, max_length=255)
    complainant_contact: Optional[str] = Field(
        None,
        max_length=320,
        description="Email or phone number. Omit for anonymous complaints.",
        examples=["patient@example.com"],
    )
    source_type: SourceType
    description: str = Field(..., min_length=10, description="Full complaint description.")
    category: Category

    @field_validator("batch_no")
    @classmethod
    def uppercase_batch(cls, v: str) -> str:
        """Normalise batch numbers to uppercase for consistent lookups."""
        return v.strip().upper()


class ComplaintUpdate(BaseModel):
    """
    Partial-update body for PATCH /complaints/{id}.
    All fields are Optional — only supplied fields are changed.
    complaint_number, id, created_at are immutable and excluded.
    """

    product_name: Optional[str] = Field(None, max_length=255)
    batch_no: Optional[str] = Field(None, max_length=100)
    complainant_name: Optional[str] = Field(None, max_length=255)
    complainant_contact: Optional[str] = Field(None, max_length=320)
    source_type: Optional[SourceType] = None
    description: Optional[str] = None
    category: Optional[Category] = None
    severity: Optional[Severity] = None   # Human QA override is allowed.
    status: Optional[Status] = None


# ======================================================================= #
# Nested response schemas (imported by ComplaintResponse)                 #
# ======================================================================= #

class ComplaintDocumentSummary(BaseModel):
    """Minimal document view embedded inside a complaint response."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_path: str
    file_type: str
    created_at: datetime


class AIAssessmentSummary(BaseModel):
    """Minimal assessment summary embedded inside a complaint response."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    risk_level: str
    summary: Optional[str]
    created_at: datetime


# ======================================================================= #
# Response schemas                                                         #
# ======================================================================= #

class ComplaintResponse(BaseModel):
    """
    Full complaint representation returned by GET /complaints/{id}.
    Built from a SQLAlchemy Complaint ORM instance via .model_validate().
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_number: str
    product_name: str
    batch_no: str
    complainant_name: str
    complainant_contact: Optional[str]
    source_type: SourceType
    description: str
    category: Category
    severity: Optional[Severity]
    status: Status
    created_at: datetime
    updated_at: datetime

    # Eagerly loaded relationships (selectin loaded by ORM).
    documents: list[ComplaintDocumentSummary] = []
    assessments: list[AIAssessmentSummary] = []


class ComplaintListItem(BaseModel):
    """
    Lightweight representation for list endpoints (GET /complaints).
    Excludes description and nested objects to keep responses lean.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_number: str
    product_name: str
    batch_no: str
    complainant_name: str
    category: Category
    severity: Optional[Severity]
    status: Status
    created_at: datetime


class ComplaintListResponse(BaseModel):
    """Paginated wrapper for complaint list endpoints."""
    items: list[ComplaintListItem]
    total: int
    page: int
    page_size: int


class IntakeExtractResponse(BaseModel):
    """
    Response returned by POST /complaints/extract when a document/text is uploaded
    before form submission for fast-filling.
    """
    product_name: Optional[str] = None
    batch_no: Optional[str] = None
    complainant_name: Optional[str] = None
    complainant_contact: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    extracted_text: Optional[str] = None

