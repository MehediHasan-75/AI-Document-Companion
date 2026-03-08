"""
File Controller Module.

Handles HTTP-facing orchestration of file operations, providing a clean
interface between routes and the file service layer.

Architecture:
    - Controller pattern separating HTTP concerns from business logic
    - Delegates to FileService for actual file operations
    - Returns standardized response structures

Integration Points:
    - WEBSOCKET_INTEGRATION: Emit upload events to connected clients
    - MQ_INTEGRATION: Queue uploaded files for processing

Example:
    >>> from src.controllers.file_controller import file_controller
    >>> result = file_controller.upload_file(uploaded_file)
    >>> print(result)  # {"file_id": "uuid-here"}
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TypedDict

from fastapi import HTTPException, UploadFile, status

from src.services.file_service import file_service


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

class UploadResult(TypedDict):
    """Type definition for successful upload response."""
    file_id: str


class UploadError(TypedDict):
    """Type definition for failed upload response."""
    file: str
    error: str


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# WEBSOCKET_INTEGRATION: Emit upload events
# Example:
#   async def emit_file_uploaded(file_id: str, filename: str) -> None:
#       await event_emitter.emit("file:uploaded", {
#           "file_id": file_id, "filename": filename
#       })

# MQ_INTEGRATION: Queue for processing
# Example:
#   async def queue_for_processing(file_id: str) -> None:
#       await message_queue.publish("file_uploaded", {"file_id": file_id})


# =============================================================================
# File Controller Implementation
# =============================================================================

class FileController:
    """
    Controller for managing file uploads and deletions.
    
    Provides HTTP-facing methods for file operations, handling error
    transformation and response formatting. Delegates actual file
    operations to the FileService.
    
    Attributes:
        service: FileService instance for file operations.
    
    Integration Points:
        - WEBSOCKET_INTEGRATION: Emit events on upload/delete
        - MQ_INTEGRATION: Queue files for async processing
    
    Example:
        >>> controller = FileController()
        >>> result = controller.upload_file(file)
        >>> print(result["file_id"])
    """

    def __init__(self) -> None:
        """
        Initialize the FileController.
        
        Sets up the connection to the FileService singleton.
        """
        self.service = file_service
        logger.debug("FileController initialized")

    # -------------------------------------------------------------------------
    # Upload Operations
    # -------------------------------------------------------------------------

    def upload_file(self, file: UploadFile) -> UploadResult:
        """
        Handle single file upload.
        
        Validates and saves a single uploaded file, returning a unique
        file identifier for subsequent operations.
        
        Args:
            file: FastAPI UploadFile instance from the request.
        
        Returns:
            Dictionary containing the file_id for the uploaded file.
        
        Raises:
            HTTPException: 400 for invalid file type.
            HTTPException: 413 for oversized file.
            HTTPException: 500 for unexpected errors.
        
        Integration Points:
            - WEBSOCKET_INTEGRATION: Emit file:uploaded event
            - MQ_INTEGRATION: Queue for automatic processing
        
        Example:
            >>> result = file_controller.upload_file(uploaded_file)
            >>> print(result)  # {"file_id": "abc-123-uuid"}
        """
        try:
            file_id = self.service.save_upload(file)
            
            logger.info("File uploaded successfully: %s", file_id)
            
            # WEBSOCKET_INTEGRATION: Emit upload event
            # await emit_file_uploaded(file_id, file.filename)
            
            # MQ_INTEGRATION: Queue for processing
            # await queue_for_processing(file_id)
            
            return {"file_id": file_id}
            
        except HTTPException:
            # Re-raise HTTP exceptions from service layer
            raise
        except Exception as exc:
            logger.exception("Unexpected error during file upload")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during upload: {str(exc)}"
            ) from exc

    # -------------------------------------------------------------------------

    def upload_multiple_files(
        self,
        files: List[UploadFile]
    ) -> List[Dict[str, Any]]:
        """
        Handle multiple file uploads.
        
        Processes each file individually, collecting results for all files.
        Continues processing remaining files even if one fails.
        
        Args:
            files: List of FastAPI UploadFile instances.
        
        Returns:
            List of dictionaries, each containing either:
                - file_id: For successful uploads
                - file + error: For failed uploads
        
        Note:
            This method does not raise exceptions for individual file
            failures. Check each result for error information.
        
        Example:
            >>> results = file_controller.upload_multiple_files([file1, file2])
            >>> for result in results:
            ...     if "error" in result:
            ...         print(f"Failed: {result['file']} - {result['error']}")
            ...     else:
            ...         print(f"Success: {result['file_id']}")
        """
        results: List[Dict[str, Any]] = []
        
        for file in files:
            try:
                results.append(self.upload_file(file))
            except HTTPException as exc:
                logger.warning(
                    "Failed to upload file %s: %s",
                    file.filename, exc.detail
                )
                results.append({
                    "file": file.filename or "unknown",
                    "error": exc.detail
                })
        
        logger.info(
            "Batch upload complete: %d succeeded, %d failed",
            sum(1 for r in results if "file_id" in r),
            sum(1 for r in results if "error" in r)
        )
        
        return results

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------

    def delete_file(self, doc_id: str) -> Dict[str, Any]:
        """
        Delete a file using its document ID.
        
        Removes the file from storage. This operation is idempotent;
        attempting to delete a non-existent file will not raise an error.
        
        Args:
            doc_id: Unique document ID assigned during upload.
        
        Returns:
            Dictionary with deletion status:
                - deleted: True if file was deleted
                - doc_id: The document ID that was deleted
        
        Integration Points:
            - WEBSOCKET_INTEGRATION: Emit file:deleted event
        
        Example:
            >>> result = file_controller.delete_file("abc-123-uuid")
            >>> print(result)  # {"deleted": True, "doc_id": "abc-123-uuid"}
        """
        deleted = self.service.delete_file(doc_id)
        
        if deleted:
            logger.info("File deleted: %s", doc_id)
        else:
            logger.debug("No file found to delete: %s", doc_id)
        
        # WEBSOCKET_INTEGRATION: Emit delete event
        # await emit_file_deleted(doc_id)
        
        return {"deleted": deleted, "doc_id": doc_id}


# =============================================================================
# Module-Level Controller Instance
# =============================================================================

# Singleton instance for dependency injection and direct usage
file_controller: FileController = FileController()