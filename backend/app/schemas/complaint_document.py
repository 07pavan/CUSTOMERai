"""
app/schemas/complaint_document.py
----------------------------------
Pydantic schemas for ComplaintDocument (file attachments).

Notes
-----
* ComplaintDocumentCreate does NOT include complaint_id — the service layer
  injects it from the URL path parameter to prevent IDOR (Insecure Direct
  Object Reference) attacks where a client could attach a document to any
  complaint by supplying an arbitrary complaint_id.

* file_path is write-only from the API perspective — it's never surfaced in
  public responses (only the file metadata is). If the path leaks cloud
  object keys, attackers could construct direct storage URLs.
  Use ComplaintDocumentResponse for API output, which includes a pre-signed
  URL field (placeholder for now).

* extracted_text is excluded from create — it's populated asynchronously
  by the background OCR/extraction worker, not by the API client.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ComplaintDocumentCreate(BaseModel):
    """
    Used internally by the upload service (not directly from client JSON).
    The API endpoint should accept `multipart/form-data` — the service layer
    converts it to this schema after saving the file.
    """
    # complaint_id injected by service layer from path param — not in body.
    file_path: str = Field(..., description="Relative storage path or object key.")
    file_type: str = Field(..., max_length=128, examples=["application/pdf"])


class ComplaintDocumentResponse(BaseModel):
    """Public document representation. file_path excluded for security."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    complaint_id: int
    file_type: str
    created_at: datetime

    # extracted_text omitted by default (can be large). Add a separate
    # endpoint GET /complaints/{id}/documents/{doc_id}/text if needed.
    has_extracted_text: bool = False  # computed in the service layer


class ComplaintDocumentTextResponse(BaseModel):
    """
    Returns the extracted text for a single document.
    Kept separate to avoid sending potentially large text in list endpoints.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    extracted_text: Optional[str]


class ComplaintDocumentUploadResponse(BaseModel):
    """
    Rich response returned by POST /complaints/{id}/documents immediately
    after a successful upload and extraction.

    Returns extracted_text in-band so the frontend can display it without
    a second round-trip.  For very large PDFs (>100 pages) the text can be
    substantial; clients should truncate display as needed.

    Fields
    ------
    detected_type   : One of 'pdf' | 'eml' | 'txt' | 'image'. Derived from
                      MIME type + extension in the upload handler.
    file_size_bytes : Actual bytes written to disk (enforced by streaming
                      counter, not from Content-Length header).
    extracted_text  : Extracted text, or None if extraction was not possible
                      (image without OCR, or extraction error).
    has_extracted_text : Convenience boolean for quick UI checks.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    file_type: str
    detected_type: str = Field(
        ...,
        examples=["pdf"],
        description="One of: pdf | eml | txt | image",
    )
    file_size_bytes: int = Field(..., description="Total bytes written to storage.")
    extracted_text: Optional[str] = Field(
        None,
        description="Raw extracted text. None for images (OCR not implemented) or failed extraction.",
    )
    has_extracted_text: bool
    created_at: datetime
