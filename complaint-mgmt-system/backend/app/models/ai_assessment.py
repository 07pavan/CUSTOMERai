"""
app/models/ai_assessment.py
-----------------------------
Stores the structured output of the LangGraph AI triage agent for a complaint.

Design decisions
-----------------
* One-to-many: a single complaint can have MULTIPLE assessments over time
  (e.g. agent re-run after new documents are uploaded, or human-triggered
  re-assessment). All historical assessments are retained for audit purposes.
  Consumers should use the latest assessment (MAX(created_at)) for the current view.

* JSONB columns (completeness_flags, raw_llm_output):
    - completeness_flags: a JSON array of objects like
        [{"field": "batch_no", "issue": "not verifiable in SAP"}, ...]
      Using JSONB (not JSONB[]) allows the schema to evolve without migrations
      and supports GIN indexing for field-level searches.
    - raw_llm_output: the complete, unprocessed LLM response payload. Stored
      for reproducibility, debugging, and potential re-parsing if the parsing
      logic changes. JSONB so it can be queried/indexed if needed.

* duplicate_of_complaint_id — nullable FK back to complaints:
    When the AI suspects this complaint is a duplicate of a prior one, it
    records the reference here. NULL means "not a known duplicate".
    The FK uses RESTRICT on delete so you cannot delete the "original"
    complaint while a duplicate reference exists — forces explicit handling.

* All text suggestion fields (root_cause_suggestion, capa_suggestion, summary)
  are nullable because:
    - Early/lightweight models may not produce all fields.
    - The completeness_flags field records what the model was unable to determine.

* risk_level is stored as a VARCHAR + SAEnum (not a PG native enum) here to
  keep it decoupled from the Severity enum on complaints — risk level (high/
  medium/low) is a continuous assessment concept; severity (critical/major/minor)
  is a regulatory classification that a human QA officer finalises.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum

from app.models.base import Base
from app.models.enums import RiskLevel

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class AIAssessment(Base):
    __tablename__ = "ai_assessments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------ #
    # Foreign keys                                                         #
    # ------------------------------------------------------------------ #
    complaint_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The complaint this assessment belongs to.",
    )

    # Nullable: NULL means not identified as a duplicate.
    duplicate_of_complaint_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(
            "complaints.id",
            ondelete="RESTRICT",   # Prevent deleting the 'original' while referenced.
            name="fk_ai_assessment_duplicate_of",
        ),
        nullable=True,
        index=True,
        comment=(
            "If AI identifies this complaint as a duplicate, this points to the original. "
            "RESTRICT on delete forces explicit deduplication before the original can be removed."
        ),
    )

    # ------------------------------------------------------------------ #
    # AI assessment outputs                                                #
    # ------------------------------------------------------------------ #
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, name="risklevel", create_type=True),
        nullable=False,
        comment="AI-assessed risk: high/medium/low. Distinct from regulatory severity.",
    )

    risk_rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="LLM-generated explanation of why this risk level was assigned.",
    )

    # JSONB / JSON: flexible list of {field, issue} objects.
    completeness_flags: Mapped[Optional[Any]] = mapped_column(
        JSON_TYPE,
        nullable=True,
        comment=(
            "Array of missing/ambiguous field flags. "
            'e.g. [{"field": "batch_no", "issue": "not verifiable"}]. '
            "NULL means the complaint was deemed complete."
        ),
    )

    root_cause_suggestion: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Hypothesised root cause(s) based on description + product history.",
    )

    capa_suggestion: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Recommended Corrective and Preventive Actions.",
    )

    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Short (2-4 sentence) executive summary of the complaint and AI findings.",
    )

    # Full raw LLM output — stored for reproducibility and debugging.
    raw_llm_output: Mapped[Optional[Any]] = mapped_column(
        JSON_TYPE,
        nullable=True,
        comment=(
            "Complete raw response from the LLM including model, usage, finish_reason. "
            "Retained for reproducibility and potential re-parsing."
        ),
    )

    # ------------------------------------------------------------------ #
    # Timestamps                                                           #
    # ------------------------------------------------------------------ #
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this specific assessment run was completed.",
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    complaint: Mapped["Complaint"] = relationship(   # noqa: F821
        "Complaint",
        back_populates="assessments",
        foreign_keys=[complaint_id],
    )

    original_complaint: Mapped[Optional["Complaint"]] = relationship(  # noqa: F821
        "Complaint",
        foreign_keys=[duplicate_of_complaint_id],
        # No back_populates needed — this is a unidirectional reference.
    )

    def __repr__(self) -> str:
        return (
            f"<AIAssessment id={self.id} "
            f"complaint_id={self.complaint_id} "
            f"risk={self.risk_level}>"
        )


from app.models.complaint import Complaint  # noqa: E402, F401
