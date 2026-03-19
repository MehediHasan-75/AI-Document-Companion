"""
Processing Routes Module
------------------------
Defines endpoints for triggering document processing and querying processing
status for previously uploaded files.
"""

from fastapi import APIRouter, BackgroundTasks, Depends

from src.dependencies.auth import get_current_user
from src.models.user import User
from src.services.process_service import process_service

router = APIRouter(prefix="/files", tags=["Processing"])


@router.post("/process/{file_id}", summary="Process an uploaded file")
def process_file(
    file_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Run the ingestion (RAG) pipeline for the given ``file_id`` in the background.
    Returns immediately with status 'processing'. Poll /status/{file_id} for updates.
    """
    return process_service.process_file_async(file_id, background_tasks)


@router.get("/status/{file_id}", summary="Get processing status for a file")
def get_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Return the current processing status for the given ``file_id``.
    """
    return process_service.get_status(file_id)

