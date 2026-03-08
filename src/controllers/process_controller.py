"""
Process Controller Module.

Handles HTTP-facing orchestration for document processing and status queries,
providing a clean interface between routes and the processing service layer.

Architecture:
    - Controller pattern separating HTTP concerns from business logic
    - Supports both synchronous and asynchronous processing
    - Delegates to ProcessService for actual processing operations

Integration Points:
    - WEBSOCKET_INTEGRATION: Real-time processing status updates
    - MQ_INTEGRATION: Job queue for distributed processing

Example:
    >>> from src.controllers.process_controller import process_controller
    >>> status = process_controller.get_status("file-uuid")
    >>> result = process_controller.process_file_async("file-uuid", bg_tasks)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, TYPE_CHECKING

from src.services.process_service import process_service

if TYPE_CHECKING:
    from fastapi import BackgroundTasks


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# WEBSOCKET_INTEGRATION: Real-time status updates
# Example:
#   async def emit_processing_status(file_id: str, status: str) -> None:
#       await event_emitter.emit("processing:status", {
#           "file_id": file_id, "status": status
#       })

# MQ_INTEGRATION: Distributed job queue
# Example:
#   async def enqueue_processing(file_id: str) -> str:
#       job_id = await message_queue.publish("processing_queue", {
#           "file_id": file_id
#       })
#       return job_id


# =============================================================================
# Process Controller Implementation
# =============================================================================

class ProcessController:
    """
    Controller for coordinating document processing operations.
    
    Provides HTTP-facing methods for triggering document processing
    and querying processing status. Supports both synchronous (blocking)
    and asynchronous (background) processing modes.
    
    Attributes:
        service: ProcessService instance for processing operations.
    
    Integration Points:
        - WEBSOCKET_INTEGRATION: Push status updates to clients
        - MQ_INTEGRATION: Use job queue for scalable processing
    
    Example:
        >>> controller = ProcessController()
        >>> status = controller.get_status("file-123")
        >>> print(status["status"])  # "uploaded"
    """

    def __init__(self) -> None:
        """
        Initialize the ProcessController.
        
        Sets up the connection to the ProcessService singleton.
        """
        self.service = process_service
        logger.debug("ProcessController initialized")

    # -------------------------------------------------------------------------
    # Processing Operations
    # -------------------------------------------------------------------------

    def process_file(self, file_id: str) -> Dict[str, Any]:
        """
        Trigger synchronous processing for a file.
        
        Initiates the RAG ingestion pipeline and blocks until completion.
        Use this for testing or when immediate results are required.
        
        Args:
            file_id: Unique identifier of the file to process.
        
        Returns:
            Dictionary containing the final processing status:
                - file_id: The file identifier
                - status: "processed" or "failed"
                - error: Error message (if failed)
        
        Raises:
            HTTPException: 404 if file does not exist.
            HTTPException: 500 if processing fails.
        
        Note:
            For production use, prefer process_file_async() to avoid
            blocking the request thread.
        
        Example:
            >>> result = process_controller.process_file("file-123")
            >>> print(result["status"])  # "processed"
        """
        logger.info("Starting synchronous processing for file: %s", file_id)
        return self.service.process_file(file_id)

    # -------------------------------------------------------------------------

    def process_file_async(
        self,
        file_id: str,
        background_tasks: "BackgroundTasks"
    ) -> Dict[str, Any]:
        """
        Trigger asynchronous processing for a file.
        
        Queues the document for background processing and returns
        immediately. Clients should poll the status endpoint to
        track progress.
        
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
            - WEBSOCKET_INTEGRATION: Push status updates to connected clients
        
        Example:
            >>> result = process_controller.process_file_async(
            ...     "file-123", background_tasks
            ... )
            >>> print(result["message"])  # "Processing started..."
        """
        logger.info("Starting async processing for file: %s", file_id)
        
        # MQ_INTEGRATION: Replace with message queue
        # job_id = await enqueue_processing(file_id)
        # return {"file_id": file_id, "job_id": job_id, "status": "queued"}
        
        return self.service.process_file_async(file_id, background_tasks)

    # -------------------------------------------------------------------------
    # Status Operations
    # -------------------------------------------------------------------------

    def get_status(self, file_id: str) -> Dict[str, Any]:
        """
        Retrieve the current processing status for a file.
        
        Returns the current state of document processing, including
        any error information if processing failed.
        
        Args:
            file_id: Unique identifier of the file.
        
        Returns:
            Dictionary containing:
                - file_id: The file identifier
                - status: One of "uploaded", "processing", "processed", "failed"
                - error: Error message (if status is "failed")
        
        Raises:
            HTTPException: 404 if file does not exist.
        
        Integration Points:
            - REDIS_INTEGRATION: Read from distributed cache
        
        Example:
            >>> status = process_controller.get_status("file-123")
            >>> if status["status"] == "processed":
            ...     print("Ready for queries!")
        """
        logger.debug("Getting status for file: %s", file_id)
        return self.service.get_status(file_id)


# =============================================================================
# Module-Level Controller Instance
# =============================================================================

# Singleton instance for dependency injection and direct usage
process_controller: ProcessController = ProcessController()

