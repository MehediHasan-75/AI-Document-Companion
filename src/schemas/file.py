"""Pydantic schemas for file and processing endpoints."""

from typing import List, Optional

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    message: str
    file_id: str


class FileUploadResultItem(BaseModel):
    file_id: Optional[str] = None
    file: Optional[str] = None
    error: Optional[str] = None


class MultiFileUploadResponse(BaseModel):
    message: str
    files: List[FileUploadResultItem]


class FileDeleteResponse(BaseModel):
    message: str
    file_id: str


class ProcessingStatusResponse(BaseModel):
    file_id: str
    status: str
    progress: Optional[float] = None
    error: Optional[str] = None


class FileItem(BaseModel):
    id: str
    filename: str
    status: str
    created_at: str
    type: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    image_count: Optional[int] = None
    table_count: Optional[int] = None


class FileListResponse(BaseModel):
    files: List[FileItem]
    total: int
    page: int
    limit: int
