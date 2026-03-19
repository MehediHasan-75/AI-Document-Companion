"""
File Routes Module
------------------

Defines file upload and deletion endpoints.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from src.core.exceptions import AppError
from src.dependencies.auth import get_current_user
from src.dependencies.db import get_db
from src.models.user import User
from src.schemas.file import FileDeleteResponse, FileListResponse, FileUploadResponse, MultiFileUploadResponse
from src.services.document_service import document_service
from src.services.file_service import file_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


@router.get(
    "",
    response_model=FileListResponse,
    summary="List all uploaded files",
    responses={401: {"description": "Invalid or expired token"}},
)
def list_files(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-based)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return document_service.list_documents(
        db, user_id=current_user.id, page=page, limit=limit
    )


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_id = file_service.save_upload(file)
    file_path = file_service.get_file_path(file_id)
    document_service.create_document(
        db,
        doc_id=file_id,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        user_id=current_user.id,
        file_path=str(file_path) if file_path else None,
        file_size=file_path.stat().st_size if file_path else None,
    )
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results: List[Dict[str, Any]] = []
    for file in files:
        try:
            file_id = file_service.save_upload(file)
            file_path = file_service.get_file_path(file_id)
            document_service.create_document(
                db,
                doc_id=file_id,
                filename=file.filename or "unknown",
                content_type=file.content_type or "application/octet-stream",
                user_id=current_user.id,
                file_path=str(file_path) if file_path else None,
                file_size=file_path.stat().st_size if file_path else None,
            )
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