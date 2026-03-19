"""
File Routes Module
------------------

Defines file upload and deletion endpoints.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse

from src.core.exceptions import AppError
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.services.file_service import file_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", summary="Upload a single file")
def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    file_id = file_service.save_upload(file)
    logger.info("File uploaded successfully: %s", file_id)
    return JSONResponse(
        status_code=201,
        content={"message": "File uploaded successfully", "file_id": file_id},
    )


@router.post("/upload/multiple", summary="Upload multiple files")
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

    return JSONResponse(
        status_code=201,
        content={"message": "Multiple file upload completed", "files": results},
    )


@router.delete("/delete", summary="Delete a file by id")
def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    file_service.delete_file(file_id)
    return JSONResponse(
        status_code=200,
        content={"message": "File deletion attempted", "file_id": file_id},
    )