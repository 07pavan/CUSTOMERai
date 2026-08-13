"""Initial schema — all four complaint management tables.

Revision ID: 0001
Revises:
Create Date: 2026-08-13

Design notes
-------------
* PostgreSQL native ENUM types are created explicitly with CREATE TYPE before
  the tables that reference them. Alembic does not auto-manage ENUM types in
  all versions — the explicit op.execute() calls below are intentional and
  idempotent (IF NOT EXISTS).

* `complaint_number_seq` is a dedicated PostgreSQL SEQUENCE for the CMP-YYYY-NNNN
  number generation. A shared sequence (not SERIAL/BIGSERIAL on the id column)
  is used because complaint_number encodes a year prefix — the service layer
  calls nextval('complaint_number_seq') and formats the string at insert time.

* Indexes are added for the most common query patterns:
    - complaints.status          (filtering by workflow state)
    - complaints.category        (regulatory reporting queries)
    - complaints.created_at      (date-range queries, GDPR / data-retention jobs)
    - complaint_documents.complaint_id   (join / lookup)
    - ai_assessments.complaint_id        (join / lookup)
    - ai_assessments.duplicate_of_complaint_id  (dedup queries)
    - audit_log.complaint_id + timestamp        (audit trail queries)

* All timestamp columns use TIMESTAMP WITH TIME ZONE (timestamptz) — UTC is
  stored in the DB; the app/client converts to local time. This is critical for
  regulatory audit trails that span time zones.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # ------------------------------------------------------------------
    # 1. Create PostgreSQL ENUM types (idempotent)
    # ------------------------------------------------------------------
    if conn.dialect.name == "postgresql":
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE sourcetype AS ENUM ('email', 'portal', 'paper', 'phone');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)

        op.execute("""
            DO $$ BEGIN
                CREATE TYPE category AS ENUM (
                    'quality', 'adverse_event', 'counterfeit', 'other'
                );
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)

        op.execute("""
            DO $$ BEGIN
                CREATE TYPE severity AS ENUM ('critical', 'major', 'minor');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)

        op.execute("""
            DO $$ BEGIN
                CREATE TYPE status AS ENUM (
                    'new', 'under_investigation', 'capa_assigned', 'closed'
                );
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)

        op.execute("""
            DO $$ BEGIN
                CREATE TYPE risklevel AS ENUM ('high', 'medium', 'low');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)

        # ------------------------------------------------------------------
        # 2. Sequence for complaint_number generation
        # ------------------------------------------------------------------
        op.execute("""
            CREATE SEQUENCE IF NOT EXISTS complaint_number_seq
                START WITH 1
                INCREMENT BY 1
                NO MINVALUE
                NO MAXVALUE
                CACHE 1;
        """)
    # Usage (in Python service layer):
    #   seq = await db.scalar(text("SELECT nextval('complaint_number_seq')"))
    #   number = f"CMP-{year}-{seq:04d}"

    # ------------------------------------------------------------------
    # 3. complaints table
    # ------------------------------------------------------------------
    op.create_table(
        "complaints",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "complaint_number",
            sa.String(20),
            nullable=False,
            comment="CMP-YYYY-NNNN. Generated via complaint_number_seq.",
        ),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column(
            "batch_no",
            sa.String(100),
            nullable=False,
            comment="Use 'UNKNOWN' when batch is not available.",
        ),
        sa.Column("complainant_name", sa.String(255), nullable=False),
        sa.Column(
            "complainant_contact",
            sa.String(320),
            nullable=True,
            comment="NULL for anonymous complaints.",
        ),
        sa.Column(
            "source_type",
            postgresql.ENUM("email", "portal", "paper", "phone", name="sourcetype", create_type=False),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM("quality", "adverse_event", "counterfeit", "other", name="category", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "severity",
            postgresql.ENUM("critical", "major", "minor", name="severity", create_type=False),
            nullable=True,
            comment="NULL until AI triage assigns it.",
        ),
        sa.Column(
            "status",
            postgresql.ENUM("new", "under_investigation", "capa_assigned", "closed", name="status", create_type=False),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("complaint_number", name="uq_complaints_number"),
        comment=(
            "Primary complaint record. Every field change must produce an audit_log entry "
            "(21 CFR Part 11 audit-trail requirement)."
        ),
    )

    # Indexes for common query patterns on complaints.
    op.create_index("ix_complaints_status",     "complaints", ["status"])
    op.create_index("ix_complaints_category",   "complaints", ["category"])
    op.create_index("ix_complaints_created_at", "complaints", ["created_at"])

    # ------------------------------------------------------------------
    # 4. complaint_documents table
    # ------------------------------------------------------------------
    op.create_table(
        "complaint_documents",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "complaint_id",
            sa.BigInteger(),
            sa.ForeignKey("complaints.id", ondelete="CASCADE", name="fk_documents_complaint"),
            nullable=False,
        ),
        sa.Column(
            "file_path",
            sa.String(1024),
            nullable=False,
            comment="Relative storage path or cloud object key.",
        ),
        sa.Column(
            "file_type",
            sa.String(128),
            nullable=False,
            comment="MIME type. More reliable than file extension.",
        ),
        sa.Column(
            "extracted_text",
            sa.Text(),
            nullable=True,
            comment="Populated asynchronously by OCR/extraction worker. NULL until ready.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_documents_complaint_id", "complaint_documents", ["complaint_id"])

    # ------------------------------------------------------------------
    # 5. ai_assessments table
    # ------------------------------------------------------------------
    op.create_table(
        "ai_assessments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "complaint_id",
            sa.BigInteger(),
            sa.ForeignKey("complaints.id", ondelete="CASCADE", name="fk_assessments_complaint"),
            nullable=False,
        ),
        sa.Column(
            "duplicate_of_complaint_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "complaints.id",
                ondelete="RESTRICT",
                name="fk_ai_assessment_duplicate_of",
            ),
            nullable=True,
            comment="RESTRICT: cannot delete the original complaint while this reference exists.",
        ),
        sa.Column(
            "risk_level",
            postgresql.ENUM("high", "medium", "low", name="risklevel", create_type=False),
            nullable=False,
        ),
        sa.Column("risk_rationale", sa.Text(), nullable=False),
        sa.Column(
            "completeness_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Array of {field, issue} objects. NULL = complaint deemed complete.',
        ),
        sa.Column("root_cause_suggestion", sa.Text(), nullable=True),
        sa.Column("capa_suggestion", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "raw_llm_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Complete raw LLM response — retained for reproducibility.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_assessments_complaint_id",     "ai_assessments", ["complaint_id"])
    op.create_index("ix_assessments_duplicate_of",     "ai_assessments", ["duplicate_of_complaint_id"])

    # GIN index on completeness_flags JSONB for field-level queries.
    op.create_index(
        "ix_assessments_completeness_flags_gin",
        "ai_assessments",
        ["completeness_flags"],
        postgresql_using="gin",
    )

    # ------------------------------------------------------------------
    # 6. audit_log table
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "complaint_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "complaints.id",
                ondelete="RESTRICT",
                name="fk_audit_log_complaint",
            ),
            nullable=False,
            comment="RESTRICT: audit history must be preserved before a complaint can be deleted.",
        ),
        sa.Column(
            "action",
            sa.String(128),
            nullable=False,
            comment="Dot-namespaced action label, e.g. 'complaint.status_changed'.",
        ),
        sa.Column(
            "actor",
            sa.String(320),
            nullable=False,
            comment="User email or 'system:ai-agent' / 'system:worker' for automated actions.",
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Action-specific payload. Schema varies by action.",
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment=(
                "Set by PostgreSQL server clock for 21 CFR Part 11 compliance. "
                "Never set by application code."
            ),
        ),
    )

    op.create_index("ix_audit_log_complaint_id", "audit_log", ["complaint_id"])
    op.create_index("ix_audit_log_timestamp",    "audit_log", ["timestamp"])

    # Composite index for the most common audit query: all events for a complaint, chronological.
    op.create_index(
        "ix_audit_log_complaint_timestamp",
        "audit_log",
        ["complaint_id", "timestamp"],
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Drop in reverse dependency order.
    # ------------------------------------------------------------------
    op.drop_table("audit_log")
    op.drop_table("ai_assessments")
    op.drop_table("complaint_documents")
    op.drop_table("complaints")

    op.execute("DROP SEQUENCE IF EXISTS complaint_number_seq;")

    # Drop ENUM types.
    op.execute("DROP TYPE IF EXISTS risklevel;")
    op.execute("DROP TYPE IF EXISTS status;")
    op.execute("DROP TYPE IF EXISTS severity;")
    op.execute("DROP TYPE IF EXISTS category;")
    op.execute("DROP TYPE IF EXISTS sourcetype;")
