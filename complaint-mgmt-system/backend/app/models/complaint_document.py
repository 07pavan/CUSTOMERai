"""
app/models/complaint_document.py
---------------------------------
Attached files for a complaint (PDFs, images, emails, lab reports, etc.).

Design decisions
----------------
* file_path stores a *relative* path (e.g. "uploads/complaints/CMP-2026-0001/photo.jpg")
  or a cloud object key (e.g. an S3 key). Storing absolute paths or full URLs
  breaks portability across environments.
* file_type is a MIME type string (e.g. "application/pdf", "image/jpeg") rather
  than just an extension — extensions are unreliable and user-controlled.
* extracted_text is nullable because:
    - Some file types (binary images without OCR) may never have text extracted.
    - Extraction is async (queued after upload) — the row is created before
      the extraction worker runs.
  When populated, this text feeds the AI assessment pipeline.
* No ON DELETE CASCADE at the DB level — we use SQLAlchemy relationship cascade
  so that deletions flow through the ORM and trigger audit hooks.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.models.base import Base


class ComplaintDocument(Base):
    __tablename__ = "complaint_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------ #
    # Foreign key                                                          #
    # ------------------------------------------------------------------ #
    complaint_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent complaint. Indexed to support fast lookup of docs per complaint.",
    )

    # ------------------------------------------------------------------ #
    # File metadata                                                        #
    # ------------------------------------------------------------------ #
    file_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment=(
            "Relative storage path or cloud object key. "
            "Never store absolute filesystem paths or full URLs here."
        ),
    )

    file_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="MIME type (e.g. 'application/pdf', 'image/jpeg'). More reliable than extension.",
    )

    # Nullable until OCR / extraction worker runs.
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Text extracted from the document (OCR for images, pdfminer for PDFs). "
            "NULL until the extraction background task completes. "
            "Fed into the AI assessment pipeline."
        ),
    )

    # ------------------------------------------------------------------ #
    # Timestamps                                                           #
    # ------------------------------------------------------------------ #
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    complaint: Mapped["Complaint"] = relationship(   # noqa: F821
        "Complaint",
        back_populates="documents",
    )

    def __repr__(self) -> str:
        return f"<ComplaintDocument id={self.id} complaint_id={self.complaint_id} type={self.file_type}>"


from app.models.complaint import Complaint  # noqa: E402, F401
