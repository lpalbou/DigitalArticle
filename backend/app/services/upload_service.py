"""
Upload service for notebook workspace files.

This is the single place responsible for:
- Filename sanitization (prevent path traversal / OS-specific path artifacts)
- Destination path resolution (guarantee writes stay inside the notebook's data/ directory)
- Streaming copy to disk (avoid loading large files fully into memory)

We intentionally keep this independent of FastAPI types to preserve separation of concerns:
the API layer passes a file-like object (BinaryIO) and a filename string.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from .file_types import get_effective_extension


class UploadError(ValueError):
    """Raised when an upload cannot be safely accepted or persisted."""


_FILENAME_ALLOWED_CHARS_RE = re.compile(r"[^A-Za-z0-9.\-_ ]+")


@dataclass(frozen=True)
class UploadLimits:
    """
    Optional size limits for uploads.

    If max_upload_bytes is None, no limit is enforced at the application layer.
    (Note: the ASGI server / reverse proxy may still enforce a request size limit.)
    """

    max_upload_bytes: Optional[int] = None


class FileUploadService:
    """Filesystem-focused upload service for a single notebook `data/` directory."""

    _MAX_FILENAME_LENGTH = 200
    _COPY_CHUNK_SIZE = 1024 * 1024  # 1MB

    def __init__(self, data_dir: Path, *, limits: Optional[UploadLimits] = None):
        self._data_dir = data_dir
        self._limits = limits or UploadLimits()

    def sanitize_filename(self, original_filename: str) -> str:
        """
        Sanitize a user-provided filename.

        - Strips any path components (both `/` and `\\` styles)
        - Replaces unsafe characters with `_`
        - Trims to a reasonable length while preserving extension (incl. `.nii.gz`)
        """
        raw = (original_filename or "").strip()
        if not raw:
            return "upload.bin"

        # Handle Windows-style paths sent by some clients
        raw = raw.replace("\\", "/")
        base = os.path.basename(raw).strip()
        base = base.replace("\x00", "")  # defensive: null-byte injection

        # Collapse repeated whitespace
        base = re.sub(r"\s+", " ", base).strip()

        # Replace unsafe characters (keep dots for extensions, hyphens/underscores, spaces)
        base = _FILENAME_ALLOWED_CHARS_RE.sub("_", base)

        # Avoid empty result after sanitization
        if not base or base in {".", ".."}:
            return "upload.bin"

        # Enforce a max length, preserving the effective extension
        if len(base) > self._MAX_FILENAME_LENGTH:
            ext = get_effective_extension(base)
            if ext and len(ext) < self._MAX_FILENAME_LENGTH:
                stem = base[: self._MAX_FILENAME_LENGTH - len(ext)]
                base = f"{stem}{ext}"
            else:
                base = base[: self._MAX_FILENAME_LENGTH]

        return base

    def resolve_destination(self, safe_filename: str) -> Path:
        """
        Resolve the final path for a safe filename, ensuring it is inside `data_dir`.
        """
        data_dir_resolved = self._data_dir.resolve()
        dest = (data_dir_resolved / safe_filename).resolve()

        # Python 3.11+ supports Path.is_relative_to
        if not dest.is_relative_to(data_dir_resolved):
            raise UploadError("Access denied: resolved path is outside notebook data directory")

        return dest

    def save_stream(self, original_filename: str, stream: BinaryIO) -> Tuple[str, int]:
        """
        Save an uploaded file from a stream into the notebook data directory.

        Returns:
            (stored_filename, bytes_written)
        """
        safe_name = self.sanitize_filename(original_filename)
        dest = self.resolve_destination(safe_name)

        bytes_written = 0
        try:
            with open(dest, "wb") as out:
                while True:
                    chunk = stream.read(self._COPY_CHUNK_SIZE)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if (
                        self._limits.max_upload_bytes is not None
                        and bytes_written > self._limits.max_upload_bytes
                    ):
                        raise UploadError(
                            f"File too large: {bytes_written} bytes (max: {self._limits.max_upload_bytes} bytes)"
                        )
                    out.write(chunk)
        except UploadError:
            # Best-effort cleanup of partial file
            try:
                if dest.exists():
                    dest.unlink()
            except Exception:
                pass
            raise

        return safe_name, bytes_written

    def delete(self, requested_filename: str) -> bool:
        """
        Delete a file in the notebook data directory.

        Returns True if deleted, False if not found.
        """
        safe_name = self.sanitize_filename(requested_filename)
        dest = self.resolve_destination(safe_name)
        if dest.exists():
            dest.unlink()
            return True
        return False

