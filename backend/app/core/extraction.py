"""
app/core/extraction.py
-----------------------
Synchronous text-extraction routines for uploaded complaint documents.

Supported formats
-----------------
  PDF          (application/pdf)     → pdfplumber page-by-page extraction
  Email        (message/rfc822 .eml) → stdlib email module (headers + body)
  Plain text   (text/plain .txt)     → UTF-8 / latin-1 read
  Image        (image/*)             → OCR STUB — returns "" (see below)

Why synchronous?
----------------
pdfplumber and the stdlib email module are CPU-bound and blocking.  They must
NOT be called directly inside an async FastAPI handler without a thread.
The documents router wraps calls with:

    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, extract_text, path, detected_type)

This offloads blocking work to the default ThreadPoolExecutor without
blocking the uvicorn event loop.

Error handling
--------------
Each extractor catches its own exceptions and returns an empty string with a
logged warning rather than raising.  A document with extraction failure is
still stored; the NULL extracted_text field signals that extraction failed or
was not applicable (image without OCR).
"""

import email
import email.policy
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# =========================================================================== #
# PDF                                                                          #
# =========================================================================== #

def extract_text_from_pdf(file_path: Path) -> str:
    """
    Extract all text from a PDF using pdfplumber.

    Why pdfplumber over pypdf?
    --------------------------
    pdfplumber provides layout-aware extraction that correctly handles:
    - Multi-column documents (common in pharma technical reports)
    - Tables (batch release certificates, lab results)
    - Wrapped text near form fields

    pypdf is faster but often strips inter-word spaces in complex layouts.

    Returns "" if the PDF has no selectable text (scanned image PDF).
    In that case, the image OCR stub would need to be applied per page —
    a future enhancement.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error(
            "pdfplumber is not installed. "
            "Run: pip install pdfplumber"
        )
        return ""

    try:
        pages: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    pages.append(f"[Page {i}]\n{text.strip()}")

        extracted = "\n\n".join(pages).strip()

        if not extracted:
            logger.warning(
                "pdfplumber found no selectable text in '%s'. "
                "The PDF may be a scanned image — OCR (extract_text_from_image) "
                "would need to be applied per page for text retrieval.",
                file_path.name,
            )

        return extracted

    except Exception as exc:
        logger.error(
            "PDF extraction failed for '%s': %s", file_path.name, exc
        )
        return ""


# =========================================================================== #
# Email (.eml)                                                                 #
# =========================================================================== #

def extract_text_from_eml(file_path: Path) -> str:
    """
    Parse an RFC-2822 email file and extract plain-text body parts.

    Uses Python's stdlib `email` with `email.policy.default` for
    proper MIME decoding and charset handling.  HTML parts are skipped —
    pharma complaint emails are typically plain-text.

    The extracted block includes:
    - Key headers (From / To / Subject / Date) for traceability
    - All text/plain MIME parts concatenated
    """
    try:
        raw = file_path.read_bytes()
        msg = email.message_from_bytes(raw, policy=email.policy.default)

        headers = "\n".join([
            f"From   : {msg.get('From',    '(unknown)')}",
            f"To     : {msg.get('To',      '(unknown)')}",
            f"Subject: {msg.get('Subject', '(no subject)')}",
            f"Date   : {msg.get('Date',    '(unknown date)')}",
        ])

        body_parts: list[str] = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_parts.append(
                            payload.decode(charset, errors="replace")
                        )
        else:
            if msg.get_content_type() == "text/plain":
                charset = msg.get_content_charset() or "utf-8"
                payload = msg.get_payload(decode=True)
                if payload:
                    body_parts.append(
                        payload.decode(charset, errors="replace")
                    )

        body = "\n\n---\n\n".join(body_parts).strip()
        return f"{headers}\n\n{'=' * 60}\n\n{body}" if body else headers

    except Exception as exc:
        logger.error(
            "Email (.eml) extraction failed for '%s': %s",
            file_path.name,
            exc,
        )
        return ""


# =========================================================================== #
# Plain text (.txt)                                                            #
# =========================================================================== #

def extract_text_from_txt(file_path: Path) -> str:
    """
    Read a plain-text file as UTF-8, falling back to latin-1 for legacy files.

    latin-1 (ISO-8859-1) is a safe fallback because it maps all 256 byte
    values to valid Unicode code points — no UnicodeDecodeError possible.
    """
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.info(
            "'%s' is not valid UTF-8 — retrying with latin-1.",
            file_path.name,
        )
        try:
            return file_path.read_text(encoding="latin-1", errors="replace")
        except Exception as exc:
            logger.error(
                "TXT extraction failed for '%s': %s", file_path.name, exc
            )
            return ""
    except Exception as exc:
        logger.error(
            "TXT extraction failed for '%s': %s", file_path.name, exc
        )
        return ""


# =========================================================================== #
# Image — OCR STUB                                                             #
# =========================================================================== #

def extract_text_from_image(file_path: Path) -> str:
    """
    OCR STUB — always returns an empty string.
    The image IS saved to disk; only text extraction is deferred.

    ╔══════════════════════════════════════════════════════════════╗
    ║  THIS IS WHERE OCR PLUGS IN — replace this function body.   ║
    ╚══════════════════════════════════════════════════════════════╝

    Option A — Tesseract (open-source, runs locally):
    ─────────────────────────────────────────────────
        pip install pytesseract Pillow

        from PIL import Image
        import pytesseract

        img = Image.open(file_path)
        return pytesseract.image_to_string(img, lang="eng")

    Option B — Azure Computer Vision (cloud, no local Tesseract needed):
    ─────────────────────────────────────────────────────────────────────
        pip install azure-cognitiveservices-vision-computervision msrest

        from azure.cognitiveservices.vision.computervision import ComputerVisionClient
        from msrest.authentication import CognitiveServicesCredentials
        import time, io

        client = ComputerVisionClient(
            settings.AZURE_VISION_ENDPOINT,
            CognitiveServicesCredentials(settings.AZURE_VISION_KEY),
        )
        with open(file_path, "rb") as img:
            operation = client.read_in_stream(img, raw=True)
        op_id = operation.headers["Operation-Location"].split("/")[-1]
        while True:
            result = client.get_read_result(op_id)
            if result.status not in ("running", "notStarted"):
                break
            time.sleep(1)
        lines = [
            line.text
            for page in result.analyze_result.read_results
            for line in page.lines
        ]
        return "\n".join(lines)

    Option C — AWS Textract:
    ─────────────────────────
        pip install boto3

        import boto3
        client = boto3.client("textract")
        response = client.detect_document_text(
            Document={"Bytes": file_path.read_bytes()}
        )
        return " ".join(
            b["Text"]
            for b in response["Blocks"]
            if b["BlockType"] == "LINE"
        )

    Option D — Google Cloud Vision:
    ─────────────────────────────────
        pip install google-cloud-vision

        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=file_path.read_bytes())
        response = client.text_detection(image=image)
        return response.full_text_annotation.text

    Note: For regulatory compliance, ensure the OCR provider's data
    processing agreement (DPA) covers patient-identifiable health data
    (HIPAA BAA / GDPR DPA as applicable to your jurisdiction).
    """
    logger.info(
        "extract_text_from_image('%s'): OCR stub called — returning empty string. "
        "Plug in an OCR library here for production text extraction.",
        file_path.name,
    )
    return ""


# =========================================================================== #
# Dispatcher                                                                   #
# =========================================================================== #

def extract_text(file_path: Path, detected_type: str) -> str:
    """
    Route to the correct extraction function based on detected file type.

    Parameters
    ----------
    file_path     : Absolute path to the saved file on disk.
    detected_type : One of 'pdf' | 'eml' | 'txt' | 'image'.

    Returns
    -------
    Extracted text (may be "" for images or extraction failures).
    Never raises — callers can always expect a string.
    """
    dispatch = {
        "pdf":   extract_text_from_pdf,
        "eml":   extract_text_from_eml,
        "txt":   extract_text_from_txt,
        "image": extract_text_from_image,
    }

    handler = dispatch.get(detected_type)
    if handler is None:
        logger.warning(
            "extract_text: unknown detected_type '%s' for '%s' — skipping.",
            detected_type,
            file_path.name,
        )
        return ""

    return handler(file_path)
