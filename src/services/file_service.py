"""
File Service Module.

Service for managing file uploads, storage, and deletions in the
document processing system.

Responsibilities:
    - Validate uploaded files against allowed MIME types and size limits
    - Persist files safely to disk with unique document IDs
    - Delete files by document ID
    - Resolve file paths from document IDs
    - Log all file operations for audit

Architecture:
    - Stateless service suitable for horizontal scaling
    - UUID-based document identification
    - Configurable upload directory and size limits
    - MIME type validation with configurable allowed types

Integration Points:
    - REDIS_INTEGRATION: Store file metadata in Redis for distributed access
    - WEBSOCKET_INTEGRATION: Emit upload progress and completion events
    - MQ_INTEGRATION: Queue uploaded files for processing
    - S3_INTEGRATION: Replace local storage with cloud object storage

Configuration:
    - UPLOAD_DIRECTORY / UPLOAD_DIR: Directory for file storage
    - MAX_FILE_SIZE / MAX_UPLOAD_SIZE: Maximum upload size in MB
    - ALLOWED_CONTENT_TYPES: Permitted MIME types

Example:
    >>> from src.services.file_service import file_service
    >>> doc_id = file_service.save_upload(uploaded_file)
    >>> file_path = file_service.get_file_path(doc_id)
    >>> file_service.delete_file(doc_id)
"""

from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Final, Optional

from fastapi import HTTPException, UploadFile, status

from src.config.environment import env
from src.config.file_types import ALLOWED_CONTENT_TYPES


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)

# Stream write chunk size (1 MB)
CHUNK_SIZE: Final[int] = 1024 * 1024


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# REDIS_INTEGRATION: File metadata storage
# Example:
#   class FileMetadataStore:
#       def save_metadata(self, doc_id: str, metadata: Dict) -> None:
#           redis_client.hset(f"file:{doc_id}", mapping=metadata)
#
#       def get_metadata(self, doc_id: str) -> Optional[Dict]:
#           return redis_client.hgetall(f"file:{doc_id}")

# WEBSOCKET_INTEGRATION: Upload progress
# Example:
#   async def emit_upload_progress(doc_id: str, bytes_written: int, total: int) -> None:
#       await event_emitter.emit("upload:progress", {
#           "doc_id": doc_id, "bytes": bytes_written, "total": total
#       })
#
#   async def emit_upload_complete(doc_id: str, filename: str) -> None:
#       await event_emitter.emit("upload:complete", {
#           "doc_id": doc_id, "filename": filename
#       })

# S3_INTEGRATION: Cloud storage
# Example:
#   class S3FileStorage:
#       def __init__(self, bucket: str):
#           self.s3 = boto3.client('s3')
#           self.bucket = bucket
#
#       async def save_upload(self, file: UploadFile) -> str:
#           doc_id = str(uuid.uuid4())
#           self.s3.upload_fileobj(file.file, self.bucket, f"{doc_id}/{file.filename}")
#           return doc_id

# MQ_INTEGRATION: Processing queue
# Example:
#   async def enqueue_for_processing(doc_id: str, file_path: str) -> None:
#       await message_queue.publish("upload_queue", {
#           "doc_id": doc_id, "file_path": file_path
#       })


# =============================================================================
# File Service Implementation
# =============================================================================

class FileService:
    """
    Service for file storage and management.

    Provides methods for saving, retrieving, and deleting uploaded files.
    Uses UUID-based document IDs for unique identification and maintains
    file metadata for retrieval.

    Attributes:
        upload_dir: Path to the upload directory for file storage.

    Integration Points:
        - REDIS_INTEGRATION: Store file metadata for distributed access
        - S3_INTEGRATION: Replace local storage with cloud storage
        - WEBSOCKET_INTEGRATION: Emit upload events

    Example:
        >>> service = FileService()
        >>> doc_id = service.save_upload(upload_file)
        >>> path = service.get_file_path(doc_id)
        >>> service.delete_file(doc_id)

    Note:
        Singleton instance created at module level as `file_service`.
        For testing, instantiate directly with custom configuration.
    """

    def __init__(self) -> None:
        """
        Initialize the FileService.

        Sets up the upload directory from environment configuration.
        Creates the directory if it doesn't exist.

        Note:
            Prefers UPLOAD_DIRECTORY if set, falls back to UPLOAD_DIR
            for backwards compatibility.
        """
        # Prefer new UPLOAD_DIRECTORY if provided, otherwise fall back to legacy UPLOAD_DIR
        upload_root = env.UPLOAD_DIRECTORY or env.UPLOAD_DIR
        self.upload_dir: Path = Path(upload_root)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Upload directory initialized at %s", self.upload_dir)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def save_upload(self, file: UploadFile) -> str:
        """
        Save an uploaded file to disk with a unique document ID.

        Validates the file against configured constraints, generates a
        unique ID, and streams the file to disk in chunks to handle
        large uploads efficiently.

        Args:
            file: FastAPI UploadFile instance from the request.

        Returns:
            Unique document ID (UUID) for the uploaded file.

        Raises:
            HTTPException: 400 if file type is not allowed.
            HTTPException: 413 if file exceeds maximum size.
            HTTPException: 500 if file write operation fails.

        Integration Points:
            - WEBSOCKET_INTEGRATION: Emit progress during upload
            - REDIS_INTEGRATION: Store file metadata after save
            - MQ_INTEGRATION: Queue file for processing after save
            - S3_INTEGRATION: Upload to S3 instead of local disk

        Example:
            >>> doc_id = file_service.save_upload(uploaded_file)
            >>> print(f"Saved with ID: {doc_id}")
        """
        self._validate_file(file)

        # Generate unique document ID
        doc_id = str(uuid.uuid4())

        # Determine file extension from original filename or MIME type
        ext = Path(file.filename).suffix if file.filename else ""
        if not ext:
            ext = mimetypes.guess_extension(file.content_type) or ".bin"

        # Construct file path: <doc_id>.<ext>
        filename = f"{doc_id}{ext}"
        file_path = self.upload_dir / filename

        try:
            # Stream write in chunks to handle large files efficiently
            bytes_written = 0
            with file_path.open("wb") as buffer:
                while chunk := file.file.read(CHUNK_SIZE):
                    buffer.write(chunk)
                    bytes_written += len(chunk)
                    
                    # WEBSOCKET_INTEGRATION: Emit progress
                    # await emit_upload_progress(doc_id, bytes_written, file_size)

            logger.info("File saved successfully: %s (%d bytes)", file_path, bytes_written)
            
            # REDIS_INTEGRATION: Store metadata
            # store_file_metadata(doc_id, {"filename": file.filename, "size": bytes_written})
            
            # MQ_INTEGRATION: Queue for processing
            # await enqueue_for_processing(doc_id, str(file_path))
            
            return doc_id

        except Exception as exc:
            logger.exception("File save operation failed for %s", file_path)
            # Clean up partial file if it exists
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File storage failed"
            ) from exc

    # -------------------------------------------------------------------------

    def delete_file(self, doc_id: str) -> bool:
        """
        Delete a file from disk using its document ID.

        Searches for and removes all files matching the document ID prefix.
        Handles missing files gracefully by logging a warning.

        Args:
            doc_id: Unique document ID of the file to delete.

        Returns:
            True if file(s) were deleted, False if no files were found.

        Integration Points:
            - REDIS_INTEGRATION: Remove file metadata from Redis
            - S3_INTEGRATION: Delete from S3 bucket

        Example:
            >>> success = file_service.delete_file("abc-123-uuid")
            >>> print(f"Deleted: {success}")
        """
        try:
            # Look for files in upload_dir that start with doc_id
            matched_files = list(self.upload_dir.glob(f"{doc_id}*"))
            
            if not matched_files:
                logger.warning("No file found with doc_id: %s", doc_id)
                return False

            for file_path in matched_files:
                file_path.unlink()
                logger.info("File deleted: %s", file_path)
                
            # REDIS_INTEGRATION: Remove metadata
            # delete_file_metadata(doc_id)
            
            return True

        except Exception:
            logger.exception("File deletion failed for doc_id: %s", doc_id)
            return False

    # -------------------------------------------------------------------------

    def get_file_path(self, doc_id: str) -> Optional[Path]:
        """
        Resolve a stored file path by its document ID prefix.

        Searches the upload directory for files matching the document ID
        and returns the path to the first match.

        Args:
            doc_id: Unique document ID assigned at upload time.

        Returns:
            Path to the matching file, or None if not found.

        Integration Points:
            - REDIS_INTEGRATION: Check metadata cache first
            - S3_INTEGRATION: Generate presigned URL instead

        Example:
            >>> path = file_service.get_file_path("abc-123-uuid")
            >>> if path:
            ...     print(f"File located at: {path}")
        """
        matched_files = list(self.upload_dir.glob(f"{doc_id}*"))
        
        if not matched_files:
            logger.debug("No file found for doc_id: %s", doc_id)
            return None
            
        return matched_files[0]

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _validate_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file against type and size constraints.

        Checks MIME type against allowed content types and file size
        against configured maximum upload size.

        Args:
            file: FastAPI UploadFile to validate.

        Raises:
            HTTPException: 400 if MIME type is not in ALLOWED_CONTENT_TYPES.
            HTTPException: 413 if file size exceeds MAX_FILE_SIZE.
        """
        # Validate MIME type
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            logger.warning(
                "Rejected upload: invalid content type %s",
                file.content_type
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} is not allowed"
            )

        # Calculate file size by seeking to end
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)  # Reset for reading

        # Prefer new MAX_FILE_SIZE if provided, otherwise fall back to legacy MAX_UPLOAD_SIZE
        max_size_mb = env.MAX_FILE_SIZE or env.MAX_UPLOAD_SIZE
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            logger.warning(
                "Rejected upload: file size %d exceeds limit %d",
                file_size, max_size_bytes
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {max_size_mb} MB"
            )


# =============================================================================
# Module-Level Service Instance
# =============================================================================

# Singleton instance for dependency injection and direct usage
file_service: FileService = FileService()