"""
File type definitions for document ingestion.

Contains allowed MIME types for RAG-compatible documents.
"""

from typing import Final


ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset({

    # PDF
    "application/pdf",

    # Plain text & markup
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/html",

    # Microsoft Word
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",

    # PowerPoint
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",

    # Excel
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

    # Structured formats
    "text/csv",
    "application/json",
})