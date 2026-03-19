"""
Processing Routes Module
------------------------
Defines endpoints for triggering document processing and querying processing
status for previously uploaded files.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.file import ProcessingStatusResponse
from src.services.process_service import process_service

router = APIRouter(prefix="/files", tags=["Processing"])


@router.post(
    "/process/{file_id}",
    summary="Process an uploaded file",
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "File not found"},
        422: {"description": "Processing failed"},
    },
)
def process_file(
    file_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Run the ingestion (RAG) pipeline for the given ``file_id`` in the background.
    Returns immediately with status 'processing'. Poll /status/{file_id} for updates.
    """
    return process_service.process_file_async(
        file_id, background_tasks, user_id=current_user.id
    )


@router.get(
    "/status/{file_id}",
    response_model=ProcessingStatusResponse,
    summary="Get processing status for a file",
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "File not found"},
    },
)
def get_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Return the current processing status for the given ``file_id``.
    """
    return process_service.get_status(file_id)
