"""
File Service Module
-------------------

Service for managing file uploads and deletions.

Responsibilities:
- Validate uploaded files against allowed MIME types and size
- Persist files safely to disk with unique doc_id
- Delete files
- Log operations
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Final
import mimetypes

from fastapi import UploadFile, HTTPException, status

from src.config.environment import env
from src.config.file_types import ALLOWED_CONTENT_TYPES

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
CHUNK_SIZE: Final[int] = 1024 * 1024  # 1 MB chunk size for streaming writes

# ------------------------------------------------------------------------------
# Logger
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# FileService Class
# ------------------------------------------------------------------------------
class FileService:
    """
    Service for file storage and management.

    Stateless and reusable across requests. Singleton instance created at module level.
    """

    def __init__(self) -> None:
        self.upload_dir = Path(env.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Upload directory initialized at %s", self.upload_dir)

    # --------------------------------------------------------------------------
    def save_upload(self, file: UploadFile) -> str:
        """
        Save an uploaded file to disk with a unique doc_id.

        Args:
            file (UploadFile): File uploaded via FastAPI.

        Returns:
            str: Unique doc_id for the uploaded file.

        Raises:
            HTTPException: On validation failure or write error.
        """
        self._validate_file(file)

        # Generate unique doc_id
        doc_id = str(uuid.uuid4())

        # Determine file extension
        ext = Path(file.filename).suffix
        if not ext:
            ext = mimetypes.guess_extension(file.content_type) or ".bin"

        # Save as <doc_id>.<ext>
        filename = f"{doc_id}{ext}"
        file_path = self.upload_dir / filename

        try:
            with file_path.open("wb") as buffer:
                while chunk := file.file.read(CHUNK_SIZE):
                    buffer.write(chunk)

            logger.info("File saved successfully: %s", file_path)
            return doc_id

        except Exception as exc:
            logger.exception("File save operation failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File storage failed"
            ) from exc

    # --------------------------------------------------------------------------
    def delete_file(self, doc_id: str) -> None:
        """
        Delete a file from disk using its doc_id.

        Args:
            doc_id (str): Unique doc_id of the file.
        """
        try:
            # Look for file in upload_dir that starts with doc_id
            matched_files = list(self.upload_dir.glob(f"{doc_id}*"))
            if not matched_files:
                logger.warning("No file found with doc_id: %s", doc_id)
                return

            for file_path in matched_files:
                file_path.unlink()
                logger.info("File deleted: %s", file_path)

        except Exception:
            logger.exception("File deletion failed for doc_id: %s", doc_id)

    # --------------------------------------------------------------------------
    def _validate_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file type and size.

        Raises:
            HTTPException: On invalid MIME type or oversized file.
        """
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} is not allowed"
            )

        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        max_size_bytes = env.MAX_UPLOAD_SIZE * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {env.MAX_UPLOAD_SIZE} MB"
            )

# ------------------------------------------------------------------------------
# Singleton instance
# ------------------------------------------------------------------------------
file_service = FileService()