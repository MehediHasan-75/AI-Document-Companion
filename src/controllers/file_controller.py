"""File controller for upload and deletion operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TypedDict

from fastapi import UploadFile

from src.core.exceptions import AppError
from src.services.file_service import file_service

logger = logging.getLogger(__name__)


class UploadResult(TypedDict):
    file_id: str


class UploadError(TypedDict):
    file: str
    error: str


class FileController:
    """Controller for managing file uploads and deletions."""

    def __init__(self) -> None:
        self.service = file_service

    def upload_file(self, file: UploadFile) -> UploadResult:
        """Handle single file upload."""
        file_id = self.service.save_upload(file)
        logger.info("File uploaded successfully: %s", file_id)
        return {"file_id": file_id}

    def upload_multiple_files(self, files: List[UploadFile]) -> List[Dict[str, Any]]:
        """Handle multiple file uploads. Continues on individual failures."""
        results: List[Dict[str, Any]] = []

        for file in files:
            try:
                results.append(self.upload_file(file))
            except AppError as exc:
                logger.warning("Failed to upload file %s: %s", file.filename, exc.message)
                results.append({
                    "file": file.filename or "unknown",
                    "error": exc.message,
                })

        return results

    def delete_file(self, doc_id: str) -> Dict[str, Any]:
        """Delete a file by document ID."""
        deleted = self.service.delete_file(doc_id)
        if deleted:
            logger.info("File deleted: %s", doc_id)
        return {"deleted": deleted, "doc_id": doc_id}


file_controller: FileController = FileController()
