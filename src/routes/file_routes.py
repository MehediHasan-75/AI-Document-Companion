"""
File Routes Module
------------------

Defines file upload and deletion endpoints.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, UploadFile

from src.core.exceptions import AppError
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.file import FileDeleteResponse, FileUploadResponse, MultiFileUploadResponse
from src.services.file_service import file_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=201,
    summary="Upload a single file",
    responses={
        400: {"description": "File validation failed"},
        401: {"description": "Invalid or expired token"},
    },
)
def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    file_id = file_service.save_upload(file)
    logger.info("File uploaded successfully: %s", file_id)
    return {"message": "File uploaded successfully", "file_id": file_id}


@router.post(
    "/upload/multiple",
    response_model=MultiFileUploadResponse,
    status_code=201,
    summary="Upload multiple files",
    responses={401: {"description": "Invalid or expired token"}},
)
def upload_multiple_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    results: List[Dict[str, Any]] = []
    for file in files:
        try:
            file_id = file_service.save_upload(file)
            results.append({"file_id": file_id})
        except AppError as exc:
            logger.warning("Failed to upload file %s: %s", file.filename, exc.message)
            results.append({"file": file.filename or "unknown", "error": exc.message})

    return {"message": "Multiple file upload completed", "files": results}


@router.delete(
    "/delete",
    response_model=FileDeleteResponse,
    summary="Delete a file by id",
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "File not found"},
    },
)
def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    file_service.delete_file(file_id)
    return {"message": "File deletion attempted", "file_id": file_id}