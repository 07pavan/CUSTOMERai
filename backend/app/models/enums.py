"""
app/models/enums.py
-------------------
Centralised Python enumerations that are mirrored as PostgreSQL native ENUM
types via SQLAlchemy's `Enum` column type.
"""

import enum


class SourceType(str, enum.Enum):
    """How the complaint arrived at the organisation."""
    pharmacy = "pharmacy"
    email    = "email"
    portal   = "portal"   # self-service web/mobile portal
    paper    = "paper"    # physical form, later digitised
    phone    = "phone"


class Category(str, enum.Enum):
    """
    Regulatory-aligned complaint categories.
    """
    quality         = "quality"           # defect, contamination, packaging, etc.
    adverse_event   = "adverse_event"     # unexpected clinical/side-effect report
    counterfeit     = "counterfeit"       # suspected falsified / substandard product
    other           = "other"


class Severity(str, enum.Enum):
    """
    ICH Q10 / GMP-aligned severity tiers.
    NULL in the DB means "not yet assessed".
    """
    critical = "critical"   # potential patient harm / recall trigger
    major    = "major"      # significant quality defect, no immediate harm
    minor    = "minor"      # cosmetic / administrative issues


class Status(str, enum.Enum):
    """
    Lifecycle states of a complaint record.
    """
    new                  = "new"
    ready_to_commit      = "ready_to_commit"  # Prepared by AI triage, awaiting QA commit
    under_investigation  = "under_investigation"
    capa_assigned        = "capa_assigned"    # Corrective And Preventive Action assigned
    closed               = "closed"


class RiskLevel(str, enum.Enum):
    """AI-assessed risk level stored on the ai_assessments table."""
    high   = "high"
    medium = "medium"
    low    = "low"
