"""
Central RAG ingestion service.

This module provides a stable ingest API for the rest of the application
while delegating to the existing implementation in
``src.services.ingestion_service``.
"""

from src.services.ingestion_service import ingest_document_pipeline

__all__ = ["ingest_document_pipeline"]

