"""
app/schemas/analytics.py
-------------------------
Pydantic schemas for the Quality Analytics Dashboard.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SeverityCount(BaseModel):
    name: str = Field(..., description="Severity label: Critical, Major, Minor, or Pending AI")
    key: str = Field(..., description="Enum key: critical, major, minor, unassessed")
    count: int


class CategoryCount(BaseModel):
    category: str = Field(..., description="Category key: quality, adverse_event, counterfeit, other")
    label: str = Field(..., description="Human-readable label")
    count: int


class ProductCount(BaseModel):
    product_name: str
    count: int


class TrendDataPoint(BaseModel):
    date: str = Field(..., description="Date string YYYY-MM-DD")
    critical: int = 0
    major: int = 0
    minor: int = 0
    total: int = 0


class StatusCount(BaseModel):
    status: str = Field(..., description="Status key")
    label: str = Field(..., description="Human-readable label")
    count: int


class AnalyticsSummaryResponse(BaseModel):
    """
    Summary response for GET /api/v1/analytics/summary
    """
    days: int = Field(..., description="Time window in days (30, 60, or 90)")
    total_complaints: int
    critical_count: int
    major_count: int
    minor_count: int
    unassessed_count: int
    active_investigations: int

    severity_breakdown: List[SeverityCount]
    category_breakdown: List[CategoryCount]
    status_breakdown: Optional[List[StatusCount]] = None
    top_products: List[ProductCount]
    trends_over_time: List[TrendDataPoint]
