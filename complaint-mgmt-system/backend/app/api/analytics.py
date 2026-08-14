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
    # Query daily counts within cutoff_date
    date_col = cast(Complaint.created_at, Date)
    trend_stmt = (
        select(
            date_col.label("cdate"),
            func.count(Complaint.id).label("total_cnt"),
            func.sum(case((Complaint.severity == Severity.critical, 1), else_=0)).label("crit_cnt"),
            func.sum(case((Complaint.severity == Severity.major, 1), else_=0)).label("maj_cnt"),
            func.sum(case((Complaint.severity == Severity.minor, 1), else_=0)).label("min_cnt"),
        )
        .where(Complaint.created_at >= cutoff_date)
        .group_by(date_col)
        .order_by(date_col.asc())
    )
    trend_results = await db.execute(trend_stmt)
    trend_map: Dict[str, TrendDataPoint] = {}

    for row in trend_results:
        dt_str = row.cdate.isoformat() if hasattr(row.cdate, "isoformat") else str(row.cdate)
        trend_map[dt_str] = TrendDataPoint(
            date=dt_str,
            critical=int(row.crit_cnt or 0),
            major=int(row.maj_cnt or 0),
            minor=int(row.min_cnt or 0),
            total=int(row.total_cnt or 0),
        )

    # Build continuous daily timeline for smooth chart rendering
    timeline: List[TrendDataPoint] = []
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days - 1)

    curr_day = start_day
    while curr_day <= today:
        dt_str = curr_day.isoformat()
        if dt_str in trend_map:
            timeline.append(trend_map[dt_str])
        else:
            timeline.append(TrendDataPoint(date=dt_str, critical=0, major=0, minor=0, total=0))
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
