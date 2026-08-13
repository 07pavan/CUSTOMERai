"""
app/core/storage.py
--------------------
Local filesystem storage for complaint document uploads.

Directory layout
----------------
    <UPLOAD_ROOT>/
      complaints/
        <complaint_id>/
          <10-char-uuid>_<sanitised-filename>

Design decisions
----------------
* Files are stored under complaints/<id>/ so that per-complaint archival,
  deletion, and S3 prefix-based access control are trivially easy.
* Filenames are prefixed with a short UUID hex to prevent collisions even
  if two uploads of "complaint.pdf" happen concurrently for the same complaint.
* User-supplied filenames are sanitised (path-traversal prevention).
* File bytes are streamed in 512 KB chunks using `aiofiles` so that large
  uploads don't block the async event loop.
* A hard 25 MB cap is enforced during streaming (not via Content-Length,
  which clients can lie about) — partial files are deleted on overflow.

S3 / cloud migration path
--------------------------
Replace `save_upload()` with a function that calls the cloud SDK.
All callers import only this one symbol, so the swap is isolated here.

Example (aiobotocore):
    async with session.create_client("s3") as s3:
        await s3.upload_fileobj(file.file, bucket, key)
    return key, file_size

Remember to update UPLOAD_ROOT usage in documents.py if you switch to a
URL-based storage key rather than a filesystem path.
"""

import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

# ------------------------------------------------------------------ #
# Configuration                                                        #
# ------------------------------------------------------------------ #

# Resolve to an absolute path so it doesn't depend on CWD at runtime.
UPLOAD_ROOT: Path = Path(settings.UPLOAD_DIR).resolve()

# Hard cap enforced by streaming byte count — clients cannot bypass via
# a falsified Content-Length header.
MAX_FILE_BYTES: int = 25 * 1024 * 1024  # 25 MB

_CHUNK_SIZE: int = 512 * 1024  # 512 KB per read


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _sanitise_filename(filename: str) -> str:
    """
    Strip directory components and replace any character that isn't
    alphanumeric, a hyphen, underscore, or dot with an underscore.

    This prevents directory traversal (e.g. '../../etc/passwd') and
    filesystem-unsafe characters on Windows/Linux simultaneously.
    """
    stem   = Path(filename).stem
    suffix = Path(filename).suffix.lower()  # normalise extension case

    safe_stem   = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    safe_suffix = "".join(c if c.isalnum() or c == "."  else "_" for c in suffix)
    return f"{safe_stem}{safe_suffix}" or "upload"


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #

async def save_upload(file: UploadFile, complaint_id: int) -> tuple[str, int]:
    """
    Stream an uploaded file to the local uploads directory.

    Parameters
    ----------
    file         : FastAPI UploadFile (multipart/form-data).
    complaint_id : Used to organise the sub-directory path.

    Returns
    -------
    (relative_path, file_size_bytes)
        relative_path   — path relative to UPLOAD_ROOT, stored in the DB.
                          Relative so the DB value is portable if UPLOAD_ROOT moves.
        file_size_bytes — total bytes written (for audit log).

    Raises
    ------
    HTTPException 413 if file exceeds MAX_FILE_BYTES.
    """
    dest_dir = UPLOAD_ROOT / "complaints" / str(complaint_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    safe_name    = _sanitise_filename(file.filename or "upload.bin")
    unique_name  = f"{uuid.uuid4().hex[:10]}_{safe_name}"
    dest_path    = dest_dir / unique_name

    total_bytes  = 0

    try:
        async with aiofiles.open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(_CHUNK_SIZE)
                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > MAX_FILE_BYTES:
                    # Delete partial file immediately — don't leave orphans on disk.
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"File exceeds the maximum allowed size of "
                            f"{MAX_FILE_BYTES // (1024 * 1024)} MB."
                        ),
                    )

                await out.write(chunk)

    except HTTPException:
        raise   # re-raise size limit error
    except Exception as exc:
        # Clean up on unexpected write errors.
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {exc}",
        ) from exc

    # Store a relative path — portable across UPLOAD_ROOT changes.
    rel_path = dest_path.relative_to(UPLOAD_ROOT).as_posix()
    return rel_path, total_bytes
