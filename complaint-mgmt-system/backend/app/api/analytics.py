"""
app/api/analytics.py
---------------------
FastAPI router for Quality Analytics & Trend Metrics.

Endpoint
--------
GET /api/v1/analytics/summary?days=30|60|90
    Returns aggregated complaint metrics:
      - Total complaints & Severity breakdown (Critical, Major, Minor, Pending AI)
      - Category breakdown (Quality Defect, Adverse Event, Counterfeit, Other)
      - Top products by complaint volume
      - Complaint volume over time (daily data points for line/area charts)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.complaint import Complaint
from app.models.enums import Category, Severity, Status
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    CategoryCount,
    ProductCount,
    SeverityCount,
    TrendDataPoint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

CATEGORY_LABELS = {
    "quality":       "Quality Defect",
    "adverse_event": "Adverse Event",
    "counterfeit":   "Counterfeit / Falsified",
    "other":         "Other",
}


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complaint analytics and trend summary",
    description=(
        "Returns aggregated complaint analytics over a specified time window "
        "(last 30, 60, or 90 days). Includes severity breakdown, category "
        "distribution, top affected products, and daily complaint volume trends."
    ),
    dependencies=[Depends(require_admin)],
)
async def get_analytics_summary(
    days: int = Query(30, ge=7, le=365, description="Time window in days (default 30)."),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryResponse:
    """
    Aggregate complaint metrics from PostgreSQL table.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # -----------------------------------------------------------------------
    # 1. Total Complaints & Key Counts
    # -----------------------------------------------------------------------
    total_stmt = select(func.count(Complaint.id))
    total_complaints: int = await db.scalar(total_stmt) or 0

    # Severity counts
    critical_stmt = select(func.count(Complaint.id)).where(Complaint.severity == Severity.critical)
    critical_count: int = await db.scalar(critical_stmt) or 0

    major_stmt = select(func.count(Complaint.id)).where(Complaint.severity == Severity.major)
    major_count: int = await db.scalar(major_stmt) or 0

    minor_stmt = select(func.count(Complaint.id)).where(Complaint.severity == Severity.minor)
    minor_count: int = await db.scalar(minor_stmt) or 0

    unassessed_stmt = select(func.count(Complaint.id)).where(Complaint.severity.is_(None))
    unassessed_count: int = await db.scalar(unassessed_stmt) or 0

    active_stmt = select(func.count(Complaint.id)).where(
        Complaint.status.in_([Status.new, Status.under_investigation, Status.capa_assigned])
    )
    active_investigations: int = await db.scalar(active_stmt) or 0

    severity_breakdown = [
        SeverityCount(name="Critical",   key="critical",   count=critical_count),
        SeverityCount(name="Major",      key="major",      count=major_count),
        SeverityCount(name="Minor",      key="minor",      count=minor_count),
        SeverityCount(name="Pending AI", key="unassessed", count=unassessed_count),
    ]

    # -----------------------------------------------------------------------
    # 2. Category Breakdown
    # -----------------------------------------------------------------------
    cat_stmt = (
        select(Complaint.complaint_category, func.count(Complaint.id))
        .group_by(Complaint.complaint_category)
    )
    cat_results = await db.execute(cat_stmt)
    cat_dict = {cat.value if hasattr(cat, "value") else str(cat): count for cat, count in cat_results}

    category_breakdown = [
        CategoryCount(
            category=cat_key,
            label=CATEGORY_LABELS.get(cat_key, cat_key.title()),
            count=cat_dict.get(cat_key, 0),
        )
        for cat_key in ["quality", "adverse_event", "counterfeit", "other"]
    ]

    # -----------------------------------------------------------------------
    # 3. Top Products Breakdown
    # -----------------------------------------------------------------------
    prod_stmt = (
        select(Complaint.product_name, func.count(Complaint.id).label("cnt"))
        .group_by(Complaint.product_name)
        .order_by(func.count(Complaint.id).desc())
        .limit(10)
    )
    prod_results = await db.execute(prod_stmt)
    top_products = [
        ProductCount(product_name=pname, count=cnt)
        for pname, cnt in prod_results
    ]

    # -----------------------------------------------------------------------
    # 4. Trends Over Time (Daily Buckets)
    # -----------------------------------------------------------------------
    trend_stmt = (
        select(Complaint.created_at, Complaint.severity)
        .where(Complaint.created_at >= cutoff_date)
    )
    trend_rows = await db.execute(trend_stmt)
    
    trend_map: Dict[str, Dict[str, int]] = {}
    for created_at_val, sev_val in trend_rows:
        if isinstance(created_at_val, str):
            dt_str = created_at_val[:10]
        elif hasattr(created_at_val, "strftime"):
            dt_str = created_at_val.strftime("%Y-%m-%d")
        else:
            dt_str = str(created_at_val)[:10]

        if dt_str not in trend_map:
            trend_map[dt_str] = {"critical": 0, "major": 0, "minor": 0, "total": 0}
        
        trend_map[dt_str]["total"] += 1
        sev_str = sev_val.value if hasattr(sev_val, "value") else str(sev_val or "")
        if sev_str == "critical":
            trend_map[dt_str]["critical"] += 1
        elif sev_str == "major":
            trend_map[dt_str]["major"] += 1
        elif sev_str == "minor":
            trend_map[dt_str]["minor"] += 1

    # Build continuous daily timeline for smooth chart rendering
    timeline: List[TrendDataPoint] = []
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days - 1)

    curr_day = start_day
    while curr_day <= today:
        dt_str = curr_day.isoformat()
        counts = trend_map.get(dt_str, {"critical": 0, "major": 0, "minor": 0, "total": 0})
        timeline.append(TrendDataPoint(
            date=dt_str,
            critical=counts["critical"],
            major=counts["major"],
            minor=counts["minor"],
            total=counts["total"],
        ))
        curr_day += timedelta(days=1)

    return AnalyticsSummaryResponse(
        days=days,
        total_complaints=total_complaints,
        critical_count=critical_count,
        major_count=major_count,
        minor_count=minor_count,
        unassessed_count=unassessed_count,
        active_investigations=active_investigations,
        severity_breakdown=severity_breakdown,
        category_breakdown=category_breakdown,
        top_products=top_products,
        trends_over_time=timeline,
    )
