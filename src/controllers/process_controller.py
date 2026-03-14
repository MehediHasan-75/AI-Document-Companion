"""Process controller for document processing operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, TYPE_CHECKING

from src.services.process_service import process_service

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)


class ProcessController:
    """Controller for triggering document processing and querying status."""

    def __init__(self) -> None:
        self.service = process_service

    def process_file_async(
        self,
        file_id: str,
        background_tasks: "BackgroundTasks",
    ) -> Dict[str, Any]:
        """Trigger asynchronous processing for a file."""
        logger.info("Starting async processing for file: %s", file_id)
        return self.service.process_file_async(file_id, background_tasks)

    def get_status(self, file_id: str) -> Dict[str, Any]:
        """Retrieve the current processing status for a file."""
        return self.service.get_status(file_id)


process_controller: ProcessController = ProcessController()
