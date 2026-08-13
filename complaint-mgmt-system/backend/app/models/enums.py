"""
app/models/enums.py
-------------------
Centralised Python enumerations that are mirrored as PostgreSQL native ENUM
types via SQLAlchemy's `Enum` column type.

Design decisions
----------------
* We inherit from (str, enum.Enum) so that enum members serialise directly to
  their string value — important for JSON responses and Pydantic compatibility.
* Native PostgreSQL ENUMs are used (native_enum=True is the SQLAlchemy default
  for the PostgreSQL dialect) because they:
    - Enforce the constraint at the DB level (not just the app layer).
    - Are more storage-efficient than VARCHAR + CHECK.
    - Show up meaningfully in pg_type, aiding DBA introspection.
* Each enum is named explicitly (via `name=`) so Alembic can track them by
  their type name rather than by column position — this makes future enum value
  additions (e.g. a new severity tier) easier to migrate.
"""

import enum


class SourceType(str, enum.Enum):
    """How the complaint arrived at the organisation."""
    email   = "email"
    portal  = "portal"   # self-service web/mobile portal
    paper   = "paper"    # physical form, later digitised
    phone   = "phone"


class Category(str, enum.Enum):
    """
    Regulatory-aligned complaint categories.
    In pharma, adverse_event complaints often require separate regulatory
    reporting (e.g. FDA MedWatch, EMA EudraVigilance) — the category flag
    drives that downstream routing.
    """
    quality         = "quality"           # defect, contamination, packaging, etc.
    adverse_event   = "adverse_event"     # unexpected clinical/side-effect report
    counterfeit     = "counterfeit"       # suspected falsified / substandard product
    other           = "other"


class Severity(str, enum.Enum):
    """
    ICH Q10 / GMP-aligned severity tiers.
    NULL in the DB means "not yet assessed" — the AI agent populates this
    after running its triage logic.
    """
    critical = "critical"   # potential patient harm / recall trigger
    major    = "major"      # significant quality defect, no immediate harm
    minor    = "minor"      # cosmetic / administrative issues


class Status(str, enum.Enum):
    """
    Lifecycle states of a complaint record.
    Every transition MUST be recorded in audit_log (21 CFR Part 11 requirement).
    """
    new                  = "new"
    under_investigation  = "under_investigation"
    capa_assigned        = "capa_assigned"    # Corrective And Preventive Action assigned
    closed               = "closed"


class RiskLevel(str, enum.Enum):
    """AI-assessed risk level stored on the ai_assessments table."""
    high   = "high"
    medium = "medium"
    low    = "low"
