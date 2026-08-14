"""
app/api/documents.py
---------------------
Document upload endpoint for complaint attachments.

Endpoint
--------
POST /api/v1/complaints/{complaint_id}/documents

Accepts
-------
multipart/form-data with a single `file` field (UploadFile).

Accepted file types (MIME + extension check)
---------------------------------------------
  PDF   application/pdf              .pdf
  Email message/rfc822               .eml
  Text  text/plain                   .txt
  Image image/jpeg|png|tiff|gif|webp .jpg .jpeg .png .tiff .tif .gif .webp .bmp

Processing pipeline
-------------------
1.  Verify complaint exists (→ 404 if not).
2.  Detect file type via MIME + extension (→ 415 if unsupported).
3.  Stream file to disk via storage.save_upload() (→ 413 if > 25 MB).
4.  Extract text in a ThreadPoolExecutor (CPU-bound, blocking).
5.  Persist ComplaintDocument ORM record.
6.  Write audit_log row in the same transaction.
7.  Commit.
8.  Return ComplaintDocumentUploadResponse with extracted_text.

Extraction notes
----------------
PDF  → pdfplumber (see extraction.py)
EML  → stdlib email parser (see extraction.py)
TXT  → UTF-8 read (see extraction.py)
IMG  → stub: returns "" (see extraction.extract_text_from_image for OCR options)
"""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_actor, get_complaint_or_404, require_admin
from app.core.audit import write_audit_log
from app.core.extraction import extract_text
from app.core.storage import UPLOAD_ROOT, save_upload
from app.db.session import get_db
from app.models.complaint_document import ComplaintDocument
from app.schemas.complaint_document import ComplaintDocumentUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["Documents"])


# ============================================================ #
# File type detection                                           #
# ============================================================ #

# MIME type → internal type label
_ALLOWED_MIME: dict[str, str] = {
    "application/pdf":    "pdf",
    "message/rfc822":     "eml",
    "text/plain":         "txt",
    "image/jpeg":         "image",
    "image/jpg":          "image",   # non-standard but common
    "image/png":          "image",
    "image/tiff":         "image",
    "image/gif":          "image",
    "image/webp":         "image",
    "image/bmp":          "image",
    # octet-stream: rely on extension fallback (some email clients send this)
}

# File extension → internal type label (fallback when MIME is generic)
_ALLOWED_EXT: dict[str, str] = {
    ".pdf":  "pdf",
    ".eml":  "eml",
    ".txt":  "txt",
    ".jpg":  "image",
    ".jpeg": "image",
    ".png":  "image",
    ".tiff": "image",
    ".tif":  "image",
    ".gif":  "image",
    ".webp": "image",
    ".bmp":  "image",
}

_ACCEPTED_TYPES_HUMAN = (
    "PDF (.pdf), email (.eml), plain text (.txt), "
    "or image (.jpg .jpeg .png .tiff .gif .webp .bmp)"
)


def _detect_file_type(content_type: str, filename: str) -> str:
    """
    Resolve the upload to one of: 'pdf' | 'eml' | 'txt' | 'image'.

    Strategy: MIME type wins; fall back to extension for clients that send
    'application/octet-stream' regardless of the actual file type.

    Raises HTTP 415 if the file type is not in the allowed set.
    """
    # Normalise: strip charset/boundary parameters ("text/plain; charset=utf-8" → "text/plain")
    mime = (content_type or "").split(";")[0].strip().lower()
    ext  = Path(filename or "").suffix.lower()

    detected = _ALLOWED_MIME.get(mime) or _ALLOWED_EXT.get(ext)

    if not detected:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type (MIME: '{mime}', extension: '{ext}'). "
                f"Accepted: {_ACCEPTED_TYPES_HUMAN}."
            ),
        )

    return detected


# ============================================================ #
# Endpoint                                                      #
# ============================================================ #

@router.post(
    "/{complaint_id}/documents",
    response_model=ComplaintDocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document attachment to a complaint",
    description=(
        "Accepts a single file upload (PDF, .eml, .txt, or image), stores it "
        "to local disk under `uploads/complaints/{complaint_id}/`, extracts "
        "raw text where possible, and persists the result to "
        "`complaint_documents.extracted_text`.\n\n"
        "Images are stored without OCR — see `app/core/extraction.py` for the "
        "OCR stub and implementation options."
    ),
    responses={
        201: {"description": "Document saved and text extracted successfully."},
        404: {"description": "Complaint not found."},
        413: {"description": "File exceeds 25 MB limit."},
        415: {"description": "Unsupported file type."},
    },
    dependencies=[Depends(require_admin)],
)
async def upload_document(
    complaint_id: int,
    file: UploadFile = File(
        ...,
        description=(
            f"File to attach. Accepted types: {_ACCEPTED_TYPES_HUMAN}. "
            "Maximum size: 25 MB."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_actor),
) -> ComplaintDocumentUploadResponse:
    """
    Full processing pipeline for a complaint document upload.

    Parameters
    ----------
    complaint_id : Path parameter — numeric PK of the target complaint.
    file         : The uploaded file (multipart/form-data).
    db           : Async database session (injected).
    actor        : Requesting user identity from X-Actor header (injected).
    """

    # ── Step 1: Verify complaint exists ─────────────────────────────────────
    await get_complaint_or_404(complaint_id, db)

    # ── Step 2: Detect and validate file type ───────────────────────────────
    detected_type = _detect_file_type(
        content_type=file.content_type or "",
        filename=file.filename or "",
    )
    # Normalised MIME for DB storage (strip charset etc.)
    normalised_mime = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()

    logger.info(
        "Uploading document for complaint %d: filename='%s', mime='%s', detected='%s'",
        complaint_id,
        file.filename,
        normalised_mime,
        detected_type,
    )

    # ── Step 3: Stream file to disk (enforces 25 MB cap) ────────────────────
    rel_path, file_size_bytes = await save_upload(file, complaint_id)
    abs_path = UPLOAD_ROOT / rel_path

    logger.info(
        "Saved complaint %d document: path='%s', size=%d bytes",
        complaint_id,
        rel_path,
        file_size_bytes,
    )

    # ── Step 4: Extract text in thread pool (CPU-bound / blocking I/O) ──────
    # run_in_executor offloads blocking work without blocking the event loop.
    # The default executor is a ThreadPoolExecutor sized by uvicorn worker count.
    loop = asyncio.get_running_loop()
    extracted_text: str = await loop.run_in_executor(
        None,           # default ThreadPoolExecutor
        extract_text,   # sync function
        abs_path,
        detected_type,
    )

    logger.info(
        "Text extraction for complaint %d document '%s': %d chars extracted.",
        complaint_id,
        file.filename,
        len(extracted_text),
    )

    # ── Step 5: Persist document record ─────────────────────────────────────
    doc = ComplaintDocument(
        complaint_id=complaint_id,
        file_path=rel_path,              # relative — portable across UPLOAD_ROOT changes
        file_type=normalised_mime,
        extracted_text=extracted_text or None,  # store NULL for empty (image/failed)
    )
    db.add(doc)
    await db.flush()  # assigns doc.id for the audit log FK

    # ── Step 6: Audit log (same transaction — atomic with doc insert) ────────
    await write_audit_log(
        db,
        complaint_id=complaint_id,
        action="document.uploaded",
        actor=actor,
        details={
            "document_id":        doc.id,
            "filename":           file.filename,
            "mime_type":          normalised_mime,
            "detected_type":      detected_type,
            "file_size_bytes":    file_size_bytes,
            "text_extracted":     bool(extracted_text),
            "extracted_char_len": len(extracted_text),
        },
    )

    # ── Step 7: Commit ────────────────────────────────────────────────────────
    await db.commit()

    # ── Step 8: Return response with extracted text ───────────────────────────
    return ComplaintDocumentUploadResponse(
        id=doc.id,
        complaint_id=complaint_id,
        file_type=normalised_mime,
        detected_type=detected_type,
        file_size_bytes=file_size_bytes,
        extracted_text=extracted_text or None,
        has_extracted_text=bool(extracted_text),
        created_at=doc.created_at,
    )
