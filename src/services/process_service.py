"""Process service for document ingestion orchestration and status tracking."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from src.core.exceptions import DocumentNotFoundError
from src.models.document import DocumentStatus
from src.services.file_service import file_service
from src.services.ingestion_service import ingest_document_pipeline

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)


class ProcessService:
    """Orchestrates document ingestion and tracks processing status."""

    def __init__(self) -> None:
        self._status_dir: Path = file_service.upload_dir / "status"
        self._status_dir.mkdir(parents=True, exist_ok=True)

    def _status_path(self, file_id: str) -> Path:
        return self._status_dir / f"{file_id}.json"

    def _write_status(
        self,
        file_id: str,
        status_value: DocumentStatus,
        error: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "file_id": file_id,
            "status": status_value.value,
        }
        if error is not None:
            payload["error"] = error

        self._status_path(file_id).write_text(json.dumps(payload))
        logger.debug("Status updated for %s: %s", file_id, status_value.value)

    def get_status(self, file_id: str) -> Dict[str, Any]:
        """Get the current processing status for a file."""
        path = self._status_path(file_id)

        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in status file for %s", file_id)

        file_path = file_service.get_file_path(file_id)
        if file_path is None:
            raise DocumentNotFoundError(f"File with id '{file_id}' not found")

        return {
            "file_id": file_id,
            "status": DocumentStatus.UPLOADED.value,
        }

    def _run_pipeline(self, file_id: str, file_path: str, user_id: str) -> None:
        """Execute the ingestion pipeline, updating status on completion or failure."""
        logger.info("Starting pipeline for file %s (user %s)", file_id, user_id)
        try:
            ingest_document_pipeline(file_path, user_id=user_id)
            self._write_status(file_id, DocumentStatus.PROCESSED)
            logger.info("Pipeline completed successfully for %s", file_id)
        except Exception as exc:
            logger.exception("Pipeline failed for %s: %s", file_id, str(exc))
            self._write_status(file_id, DocumentStatus.FAILED, str(exc))

    def process_file_async(
        self,
        file_id: str,
        background_tasks: "BackgroundTasks",
        user_id: str,
    ) -> Dict[str, Any]:
        """Queue the file for background processing."""
        file_path = file_service.get_file_path(file_id)
        if file_path is None:
            raise DocumentNotFoundError(f"File with id '{file_id}' not found")

        self._write_status(file_id, DocumentStatus.PROCESSING)
        background_tasks.add_task(self._run_pipeline, file_id, str(file_path), user_id)
        logger.info("Async processing started for %s", file_id)

        return {
            "file_id": file_id,
            "status": DocumentStatus.PROCESSING.value,
            "message": "Processing started. Poll /files/status/{file_id} for updates.",
        }


process_service: ProcessService = ProcessService()
