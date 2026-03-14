"""Main application entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    AppError,
    DocumentNotFoundError,
    FileNotFoundError,
    FileValidationError,
    VectorStoreError,
)
from src.core.logger import setup_logging
from src.routes import index

setup_logging()

app = FastAPI(
    title="AI Document Companion API",
    version="1.0.0",
    description="API for managing files",
)

# Global exception handler
_STATUS_MAP = {
    FileNotFoundError: 404,
    DocumentNotFoundError: 404,
    FileValidationError: 400,
    VectorStoreError: 503,
}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_code = _STATUS_MAP.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content={"detail": exc.message})


app.include_router(index.router)


@app.get("/", summary="API Root")
async def root():
    return {"message": "AI Document Companion API is running"}
