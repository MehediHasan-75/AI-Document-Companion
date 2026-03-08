"""
File Routes Module
------------------

Defines file upload and deletion endpoints.
"""

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List

from src.controllers.file_controller import file_controller

router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/upload", summary="Upload a single file")
async def upload_file(file: UploadFile = File(...)):
    result = file_controller.upload_file(file)
    return JSONResponse(
        status_code=201,
        content={
            "message": "File uploaded successfully",
            "file_id": result["file_id"],
        },
    )

@router.post("/upload/multiple", summary="Upload multiple files")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    results = file_controller.upload_multiple_files(files)
    return JSONResponse(
        status_code=201,
        content={
            "message": "Multiple file upload completed",
            "files": results,
        },
    )

@router.delete("/delete", summary="Delete a file by id")
async def delete_file(file_id: str):
    file_controller.delete_file(file_id)
    return JSONResponse(
        status_code=200,
        content={
            "message": "File deletion attempted",
            "file_id": file_id,
        },
    )