"""
Process Service Module.

Coordinates document processing (RAG ingestion) and file-level status
tracking using the filesystem for persistence.

Architecture:
    - Orchestrates document ingestion pipeline
    - Tracks processing status per file (uploaded, processing, processed, failed)
    - Supports both synchronous and asynchronous processing
    - Status stored as JSON files in status directory

Integration Points:
    - REDIS_INTEGRATION: Store status in Redis for distributed deployments
    - WEBSOCKET_INTEGRATION: Real-time status updates to clients
    - MQ_INTEGRATION: Use message queue for async job processing

Status Flow:
    uploaded -> processing -> processed
                          \\-> failed

Example:
    >>> from src.services.process_service import process_service
    >>> status = process_service.get_status("file-uuid")
    >>> result = process_service.process_file_async("file-uuid", background_tasks)
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from fastapi import HTTPException, status

from src.services.file_service import file_service
from src.services.ingestion_service import ingest_document_pipeline

if TYPE_CHECKING:
    from fastapi import BackgroundTasks


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Status Enumeration
# =============================================================================


class FileProcessingStatus(str, Enum):
    """
    Enumeration of file processing states.
    
    Inherits from str for JSON serialization compatibility.
    
    Attributes:
        UPLOADED: File has been uploaded but not yet processed.
        PROCESSING: File is currently being processed.
        PROCESSED: File has been successfully processed.
        FAILED: Processing failed with an error.
    """
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# REDIS_INTEGRATION: Distributed status storage
# Example:
#   class RedisStatusStore:
#       def write_status(self, file_id: str, status_data: Dict) -> None:
#           redis_client.setex(f"status:{file_id}", 86400, json.dumps(status_data))
#
#       def get_status(self, file_id: str) -> Optional[Dict]:
#           data = redis_client.get(f"status:{file_id}")
#           return json.loads(data) if data else None

# WEBSOCKET_INTEGRATION: Real-time status updates
# Example:
#   async def emit_status_change(file_id: str, status: str) -> None:
#       await event_emitter.emit("file:status", {
#           "file_id": file_id, "status": status
#       })

# MQ_INTEGRATION: Job queue for processing
# Example:
#   async def enqueue_processing_job(file_id: str, file_path: str) -> str:
#       job_id = str(uuid.uuid4())
#       await message_queue.publish("processing_queue", {
#           "job_id": job_id, "file_id": file_id, "file_path": file_path
#       })
#       return job_id


# =============================================================================
# Process Service Implementation
# =============================================================================


class ProcessService:
    """
    Service for orchestrating document ingestion into the RAG pipeline.
    
    Manages the lifecycle of document processing, from upload through
    ingestion, tracking status at each stage. Supports both synchronous
    processing (blocking) and asynchronous processing (background tasks).
    
    Attributes:
        _status_dir: Directory for storing status JSON files.
    
    Integration Points:
        - REDIS_INTEGRATION: Replace file-based status with Redis
        - WEBSOCKET_INTEGRATION: Emit real-time status changes
        - MQ_INTEGRATION: Use job queue for processing
    
    Example:
        >>> service = ProcessService()
        >>> status = service.get_status("file-123")
        >>> print(status["status"])  # "uploaded"
    """

    def __init__(self) -> None:
        """
        Initialize the ProcessService.
        
        Sets up the status directory for storing processing state.
        Creates the directory if it doesn't exist.
        """
        # Store status metadata alongside uploaded files
        self._status_dir: Path = file_service.upload_dir / "status"
        self._status_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug("ProcessService initialized with status_dir: %s", self._status_dir)

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------
    def _status_path(self, file_id: str) -> Path:
        """
        Get the path to a file's status JSON file.
        
        Args:
            file_id: Unique identifier of the file.
        
        Returns:
            Path to the status JSON file.
        """
        return self._status_dir / f"{file_id}.json"

    # -------------------------------------------------------------------------
    def _write_status(
        self,
        file_id: str,
        status_value: FileProcessingStatus,
        error: Optional[str] = None,
    ) -> None:
        """
        Write processing status to disk.
        
        Persists the current processing state for a file as a JSON file.
        Optionally includes error information for failed processing.
        
        Args:
            file_id: Unique identifier of the file.
            status_value: Current processing status.
            error: Optional error message if processing failed.
        
        Integration Points:
            - REDIS_INTEGRATION: Write to Redis instead of filesystem
            - WEBSOCKET_INTEGRATION: Emit status change event
        """
        payload: Dict[str, Any] = {
            "file_id": file_id,
            "status": status_value.value,
        }
        if error is not None:
            payload["error"] = error

        path = self._status_path(file_id)
        path.write_text(json.dumps(payload))
        
        logger.debug("Status updated for %s: %s", file_id, status_value.value)
        
        # WEBSOCKET_INTEGRATION: Emit status change
        # await emit_status_change(file_id, status_value.value)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def get_status(self, file_id: str) -> Dict[str, Any]:
        """
        Get the current processing status for a file.
        
        Retrieves the persisted status from the filesystem. If no explicit
        status has been recorded but the file exists on disk, it is
        treated as ``uploaded``.
        
        Args:
            file_id: Unique identifier of the file.
        
        Returns:
            Dictionary containing:
                - file_id: The file identifier
                - status: Current status string
                - error: Error message (if status is "failed")
        
        Raises:
            HTTPException: 404 if file does not exist.
        
        Integration Points:
            - REDIS_INTEGRATION: Read from Redis cache first
        
        Example:
            >>> status = process_service.get_status("abc-123")
            >>> print(status)  # {"file_id": "abc-123", "status": "processed"}
        """
        path = self._status_path(file_id)
        
        # Try to read from persisted status file
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in status file for %s", file_id)
                # Fall through to recompute from disk

        # If we reach here, no valid status is stored; infer from filesystem
        file_path = file_service.get_file_path(file_id)
        if file_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with id '{file_id}' not found",
            )

        return {
            "file_id": file_id,
            "status": FileProcessingStatus.UPLOADED.value,
        }

    # -------------------------------------------------------------------------
    def _run_pipeline(self, file_id: str, file_path: str) -> None:
        """
        Execute the ingestion pipeline for a file.
        
        Internal method called by background tasks. Handles success and
        failure status updates.
        
        Args:
            file_id: Unique identifier of the file.
            file_path: Absolute path to the file on disk.
        
        Note:
            This method catches all exceptions and writes failure status
            rather than propagating errors.
        """
        logger.info("Starting pipeline for file %s", file_id)
        
        try:
            ingest_document_pipeline(file_path)
            self._write_status(file_id, FileProcessingStatus.PROCESSED)
            logger.info("Pipeline completed successfully for %s", file_id)
            
        except Exception as exc:
            logger.exception("Pipeline failed for %s: %s", file_id, str(exc))
            self._write_status(file_id, FileProcessingStatus.FAILED, str(exc))

    # -------------------------------------------------------------------------
    def process_file_async(
        self,
        file_id: str,
        background_tasks: "BackgroundTasks"
    ) -> Dict[str, Any]:
        """
        Start the ingestion pipeline in the background.
        
        Queues the document for processing and returns immediately.
        Clients should poll the status endpoint to track progress.
        
        Args:
            file_id: Unique identifier of the file to process.
            background_tasks: FastAPI BackgroundTasks instance for
                scheduling the processing task.
        
        Returns:
            Dictionary containing:
                - file_id: The file identifier
                - status: "processing"
                - message: Instructions for polling status
        
        Raises:
            HTTPException: 404 if file does not exist.
        
        Integration Points:
            - MQ_INTEGRATION: Use message queue instead of BackgroundTasks
            - WEBSOCKET_INTEGRATION: Push status updates to clients
        
        Example:
            >>> result = process_service.process_file_async(
            ...     "file-123", background_tasks
            ... )
            >>> print(result["status"])  # "processing"
        """
        file_path = file_service.get_file_path(file_id)
        if file_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with id '{file_id}' not found",
            )

        # Mark as processing
        self._write_status(file_id, FileProcessingStatus.PROCESSING)

        # Add to background tasks
        # MQ_INTEGRATION: Replace with message queue publish
        background_tasks.add_task(self._run_pipeline, file_id, str(file_path))
        
        logger.info("Async processing started for %s", file_id)

        return {
            "file_id": file_id,
            "status": FileProcessingStatus.PROCESSING.value,
            "message": "Processing started. Poll /files/status/{file_id} for updates."
        }

    # -------------------------------------------------------------------------
    def process_file(self, file_id: str) -> Dict[str, Any]:
        """
        Run the ingestion pipeline synchronously (blocking).
        
        Processes the document and blocks until completion. Use this
        for testing or when immediate results are required.
        
        Args:
            file_id: Unique identifier of the file to process.
        
        Returns:
            Dictionary containing the final processing status.
        
        Raises:
            HTTPException: 404 if file does not exist.
            HTTPException: 500 if processing fails.
        
        Note:
            For production use, prefer process_file_async() to avoid
            blocking the request thread during long-running processing.
        
        Example:
            >>> result = process_service.process_file("file-123")
            >>> print(result["status"])  # "processed"
        """
        file_path = file_service.get_file_path(file_id)
        if file_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with id '{file_id}' not found",
            )

        self._write_status(file_id, FileProcessingStatus.PROCESSING)
        
        logger.info("Synchronous processing started for %s", file_id)

        try:
            ingest_document_pipeline(str(file_path))
        except Exception as exc:
            logger.exception("Processing failed for %s", file_id)
            self._write_status(file_id, FileProcessingStatus.FAILED, str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected error during document processing",
            ) from exc

        self._write_status(file_id, FileProcessingStatus.PROCESSED)
        logger.info("Synchronous processing completed for %s", file_id)
        
        return self.get_status(file_id)


# =============================================================================
# Module-Level Service Instance
# =============================================================================

# Singleton instance for dependency injection and direct usage
process_service: ProcessService = ProcessService()

