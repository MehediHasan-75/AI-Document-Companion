"""Main application entry point."""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.exceptions import (
    AppError,
    AuthenticationError,
    ConflictError,
    DocumentNotFoundError,
    FileNotFoundError,
    FileValidationError,
    VectorStoreError,
)
from src.core.logger import setup_logging
from src.db.session import init_db
from src.routes import index

setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Document Companion API",
    version="1.0.0",
    description="API for managing files",
)

# ── Middleware ────────────────────────────────────────────────────────────────
# Registration order matters: last added = outermost (first to handle request).
# Execution order: CORS → GZip → request logging → route handler

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log method, path, status code, and response time for every request."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d  (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ── Exception handlers ────────────────────────────────────────────────────────
_STATUS_MAP = {
    FileNotFoundError: 404,
    DocumentNotFoundError: 404,
    FileValidationError: 400,
    VectorStoreError: 503,
    AuthenticationError: 401,
    ConflictError: 409,
}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_code = _STATUS_MAP.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content={"detail": exc.message})


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(index.router)


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    init_db()


@app.get("/", summary="API Root")
async def root():
    return {"message": "AI Document Companion API is running"}
