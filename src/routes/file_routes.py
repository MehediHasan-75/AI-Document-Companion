"""
File Routes Module
------------------

Defines file upload and deletion endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse

from src.controllers.file_controller import file_controller
from src.dependencies.auth import get_current_user
from src.models.user import User

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", summary="Upload a single file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    result = file_controller.upload_file(file)
    return JSONResponse(
        status_code=201,
        content={"message": "File uploaded successfully", "file_id": result["file_id"]},
    )


@router.post("/upload/multiple", summary="Upload multiple files")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    results = file_controller.upload_multiple_files(files)
    return JSONResponse(
        status_code=201,
        content={"message": "Multiple file upload completed", "files": results},
    )


@router.delete("/delete", summary="Delete a file by id")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    file_controller.delete_file(file_id)
    return JSONResponse(
        status_code=200,
        content={"message": "File deletion attempted", "file_id": file_id},
    )