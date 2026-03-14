"""File service for upload storage and management."""

from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from src.config import settings
from src.config.constants import FILE_WRITE_CHUNK_SIZE
from src.config.file_types import ALLOWED_CONTENT_TYPES
from src.core.exceptions import FileNotFoundError, FileValidationError

logger = logging.getLogger(__name__)


class FileService:
    """Service for file storage, retrieval, and deletion."""

    def __init__(self) -> None:
        upload_root = settings.UPLOAD_DIRECTORY or settings.UPLOAD_DIR
        self.upload_dir: Path = Path(upload_root)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Upload directory initialized at %s", self.upload_dir)

    def save_upload(self, file: UploadFile) -> str:
        """Validate, save an uploaded file, and return its unique document ID."""
        self._validate_file(file)

        doc_id = str(uuid.uuid4())

        ext = Path(file.filename).suffix if file.filename else ""
        if not ext:
            ext = mimetypes.guess_extension(file.content_type) or ".bin"

        filename = f"{doc_id}{ext}"
        file_path = self.upload_dir / filename

        try:
            bytes_written = 0
            with file_path.open("wb") as buffer:
                while chunk := file.file.read(FILE_WRITE_CHUNK_SIZE):
                    buffer.write(chunk)
                    bytes_written += len(chunk)

            logger.info("File saved successfully: %s (%d bytes)", file_path, bytes_written)
            return doc_id

        except Exception as exc:
            logger.exception("File save operation failed for %s", file_path)
            if file_path.exists():
                file_path.unlink()
            raise FileValidationError("File storage failed") from exc

    def delete_file(self, doc_id: str) -> bool:
        """Delete all files matching the document ID. Returns True if any were deleted."""
        try:
            matched_files = list(self.upload_dir.glob(f"{doc_id}*"))
            if not matched_files:
                logger.warning("No file found with doc_id: %s", doc_id)
                return False

            for file_path in matched_files:
                file_path.unlink()
                logger.info("File deleted: %s", file_path)

            return True
        except Exception:
            logger.exception("File deletion failed for doc_id: %s", doc_id)
            return False

    def get_file_path(self, doc_id: str) -> Optional[Path]:
        """Resolve a stored file path by its document ID prefix."""
        matched_files = list(self.upload_dir.glob(f"{doc_id}*"))
        if not matched_files:
            return None
        return matched_files[0]

    def _validate_file(self, file: UploadFile) -> None:
        """Validate file against allowed MIME types and size limits."""
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise FileValidationError(f"File type {file.content_type} is not allowed")

        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        max_size_mb = settings.MAX_FILE_SIZE or settings.MAX_UPLOAD_SIZE
        max_size_bytes = max_size_mb * 1024 * 1024

        if file_size > max_size_bytes:
            raise FileValidationError(f"File exceeds maximum size of {max_size_mb} MB")


file_service: FileService = FileService()
