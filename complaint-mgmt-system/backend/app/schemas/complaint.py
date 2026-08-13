"""
app/schemas/complaint.py
-------------------------
Pydantic v2 request/response schemas for the Complaint resource,
matching exact field specifications.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import Category, Severity, SourceType, Status


# ======================================================================= #
# Request schemas                                                          #
# ======================================================================= #

class ComplaintCreate(BaseModel):
    """
    Body expected when a new complaint is submitted via POST /complaints.
    """
    model_config = ConfigDict(populate_by_name=True)

    complaint_source: SourceType = Field(..., alias="source_type", examples=["email"])
    customer_name: str = Field(..., min_length=1, max_length=255, alias="complainant_name", examples=["St. Jude Pharmacy"])
    complainant_contact: Optional[str] = Field(None, max_length=320, examples=["qa@stjude.org"])
    product_name: str = Field(..., min_length=1, max_length=255, examples=["Amoxicillin 500mg"])
    product_strength: Optional[str] = Field(None, max_length=100, examples=["500mg"])
    batch_no: str = Field(..., min_length=1, max_length=100, examples=["BT20260401"])
    affected_quantity: Optional[str] = Field(None, max_length=100, examples=["1500 tablets"])
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    originating_site_block: Optional[str] = Field(None, max_length=255, examples=["Block B-4"])
    impacted_npm: Optional[str] = Field(None, max_length=255, examples=["NPM-9901"])
    complaint_category: Category = Field(..., alias="category", examples=["quality"])
    complaint_description: str = Field(..., min_length=10, alias="description", examples=["Discoloration observed on tablets."])
    severity: Optional[Severity] = None
    suggested_next_action: Optional[str] = None
    initial_risk_assessment: Optional[str] = None

    @field_validator("batch_no")
    @classmethod
    def uppercase_batch(cls, v: str) -> str:
        return v.strip().upper() if v else "UNKNOWN"

    # Backward compatibility properties for code expecting old names
    @property
    def source_type(self) -> SourceType:
        return self.complaint_source

    @property
    def complainant_name(self) -> str:
        return self.customer_name

    @property
    def category(self) -> Category:
        return self.complaint_category

    @property
    def description(self) -> str:
        return self.complaint_description


class ComplaintUpdate(BaseModel):
    """
    Partial-update body for PATCH /complaints/{id}.
    """
    model_config = ConfigDict(populate_by_name=True)

    complaint_source: Optional[SourceType] = Field(None, alias="source_type")
    customer_name: Optional[str] = Field(None, max_length=255, alias="complainant_name")
    complainant_contact: Optional[str] = Field(None, max_length=320)
    product_name: Optional[str] = Field(None, max_length=255)
    product_strength: Optional[str] = Field(None, max_length=100)
    batch_no: Optional[str] = Field(None, max_length=100)
    affected_quantity: Optional[str] = Field(None, max_length=100)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    originating_site_block: Optional[str] = Field(None, max_length=255)
    impacted_npm: Optional[str] = Field(None, max_length=255)
    complaint_category: Optional[Category] = Field(None, alias="category")
    complaint_description: Optional[str] = Field(None, alias="description")
    severity: Optional[Severity] = None
    suggested_next_action: Optional[str] = None
    initial_risk_assessment: Optional[str] = None
    status: Optional[Status] = None


# ======================================================================= #
# Nested response schemas                                                  #
# ======================================================================= #

class ComplaintDocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_path: str
    file_type: str
    created_at: datetime


class AIAssessmentSummary(BaseModel):
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
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    complaint_number: str
    complaint_source: SourceType
    customer_name: str
    complainant_contact: Optional[str] = None
    product_name: str
    product_strength: Optional[str] = None
    batch_no: str
    affected_quantity: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    originating_site_block: Optional[str] = None
    impacted_npm: Optional[str] = None
    complaint_category: Category
    complaint_description: str
    severity: Optional[Severity] = None
    suggested_next_action: Optional[str] = None
    initial_risk_assessment: Optional[str] = None
    status: Status
    created_at: datetime
    updated_at: datetime

    # Aliases for frontend backward compatibility
    @property
    def source_type(self) -> SourceType:
        return self.complaint_source

    @property
    def complainant_name(self) -> str:
        return self.customer_name

    @property
    def category(self) -> Category:
        return self.complaint_category

    @property
    def description(self) -> str:
        return self.complaint_description

    documents: list[ComplaintDocumentSummary] = []
    assessments: list[AIAssessmentSummary] = []


class ComplaintListItem(BaseModel):
    """
    Lightweight representation for list endpoints (GET /complaints).
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    complaint_number: str
    complaint_source: SourceType
    customer_name: str
    product_name: str
    product_strength: Optional[str] = None
    batch_no: str
    complaint_category: Category
    severity: Optional[Severity] = None
    status: Status
    created_at: datetime

    @property
    def source_type(self) -> SourceType:
        return self.complaint_source

    @property
    def complainant_name(self) -> str:
        return self.customer_name

    @property
    def category(self) -> Category:
        return self.complaint_category


class ComplaintListResponse(BaseModel):
    items: list[ComplaintListItem]
    total: int
    page: int
    page_size: int


class IntakeExtractResponse(BaseModel):
    """
    Response returned by POST /complaints/extract.
    """
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    complainant_contact: Optional[str] = None
    product_name: Optional[str] = None
    product_strength: Optional[str] = None
    batch_no: Optional[str] = None
    affected_quantity: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    originating_site_block: Optional[str] = None
    impacted_npm: Optional[str] = None
    complaint_category: Optional[str] = None
    complaint_description: Optional[str] = None
    suggested_next_action: Optional[str] = None
    initial_risk_assessment: Optional[str] = None
    extracted_text: Optional[str] = None

    # Aliases
    @property
    def source_type(self) -> Optional[str]:
        return self.complaint_source

    @property
    def complainant_name(self) -> Optional[str]:
        return self.customer_name

    @property
    def category(self) -> Optional[str]:
        return self.complaint_category

    @property
    def description(self) -> Optional[str]:
        return self.complaint_description
