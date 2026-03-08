"""
Processing Routes Module
------------------------
Defines endpoints for triggering document processing and querying processing
status for previously uploaded files.
"""

from fastapi import APIRouter, BackgroundTasks

from src.controllers.process_controller import process_controller


router = APIRouter(prefix="/files", tags=["Processing"])


@router.post("/process/{file_id}", summary="Process an uploaded file")
async def process_file(file_id: str, background_tasks: BackgroundTasks):
    """
    Run the ingestion (RAG) pipeline for the given ``file_id`` in the background.
    Returns immediately with status 'processing'. Poll /status/{file_id} for updates.
    """
    return process_controller.process_file_async(file_id, background_tasks)


@router.get("/status/{file_id}", summary="Get processing status for a file")
async def get_status(file_id: str):
    """
    Return the current processing status for the given ``file_id``.
    """
    return process_controller.get_status(file_id)

