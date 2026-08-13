"""
app/models/complaint.py
-----------------------
Core complaint record with exact schema alignment.
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Date, DateTime, Enum as SAEnum,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Category, Severity, SourceType, Status


class Complaint(Base):
    __tablename__ = "complaints"

    __table_args__ = (
        UniqueConstraint("complaint_number", name="uq_complaints_number"),
        {
            "comment": (
                "Primary complaint record. Every field change MUST produce an "
                "audit_log entry to satisfy 21 CFR Part 11 audit-trail requirements."
            )
        },
    )

    # ------------------------------------------------------------------ #
    # Primary key & Identifier                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    complaint_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        comment="CMP-YYYY-NNNN format.",
    )

    # ------------------------------------------------------------------ #
    # Core complaint fields                                                #
    # ------------------------------------------------------------------ #
    complaint_source: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, name="sourcetype", create_type=True),
        nullable=False,
        comment="Pharmacy / Email / Portal / Phone / Paper",
    )

    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    complainant_contact: Mapped[Optional[str]] = mapped_column(
        String(320),
        nullable=True,
        comment="Email or phone. NULL for anonymous submissions.",
    )

    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Trade name or INN of the product.",
    )

    product_strength: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Strength or dosage form concentration (e.g. 500mg, 10mg/mL).",
    )

    batch_no: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Batch/lot number for traceability.",
    )

    affected_quantity: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Quantity of affected product units (e.g. 1500 tablets, 3 vials).",
    )

    manufacturing_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Batch manufacturing date.",
    )

    expiry_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Batch expiration date.",
    )

    originating_site_block: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Manufacturing site or production block (e.g. Block B-4, Site 2).",
    )

    impacted_npm: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Impacted New Product / Material code or SAP material ID.",
    )

    complaint_category: Mapped[Category] = mapped_column(
        SAEnum(Category, name="category", create_type=True),
        nullable=False,
        comment="Quality / Adverse Event / Counterfeit / Other",
    )

    complaint_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full verbatim complaint text.",
    )

    # ------------------------------------------------------------------ #
    # Risk & Assessment fields                                             #
    # ------------------------------------------------------------------ #
    severity: Mapped[Optional[Severity]] = mapped_column(
        SAEnum(Severity, name="severity", create_type=True),
        nullable=True,
        comment="Critical / Major / Minor (NULL until AI triage or QA assessment).",
    )

    suggested_next_action: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Recommended immediate investigation step or triage action.",
    )

    initial_risk_assessment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Initial GXP risk evaluation rationale.",
    )

    status: Mapped[Status] = mapped_column(
        SAEnum(Status, name="status", create_type=True),
        nullable=False,
        server_default="new",
        comment="new / ready_to_commit / under_investigation / capa_assigned / closed",
    )

    # ------------------------------------------------------------------ #
    # Timestamps                                                           #
    # ------------------------------------------------------------------ #
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ------------------------------------------------------------------ #
    # Backwards-compatibility property aliases                          #
    # ------------------------------------------------------------------ #
    @property
    def source_type(self) -> SourceType:
        return self.complaint_source

    @source_type.setter
    def source_type(self, val: SourceType):
        self.complaint_source = val

    @property
    def complainant_name(self) -> str:
        return self.customer_name

    @complainant_name.setter
    def complainant_name(self, val: str):
        self.customer_name = val

    @property
    def category(self) -> Category:
        return self.complaint_category

    @category.setter
    def category(self, val: Category):
        self.complaint_category = val

    @property
    def description(self) -> str:
        return self.complaint_description

    @description.setter
    def description(self, val: str):
        self.complaint_description = val

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    documents: Mapped[list["ComplaintDocument"]] = relationship(   # noqa: F821
        "ComplaintDocument",
        back_populates="complaint",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    assessments: Mapped[list["AIAssessment"]] = relationship(      # noqa: F821
        "AIAssessment",
        back_populates="complaint",
        foreign_keys="AIAssessment.complaint_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(           # noqa: F821
        "AuditLog",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="AuditLog.timestamp",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Complaint {self.complaint_number} customer={self.customer_name!r} status={self.status}>"


from app.models.complaint_document import ComplaintDocument  # noqa: E402, F401
from app.models.ai_assessment import AIAssessment            # noqa: E402, F401
from app.models.audit_log import AuditLog                    # noqa: E402, F401
