"""
Facade for Unstructured-based PDF partitioning used by the RAG pipeline.

Delegates to the existing implementation in ``src.services.unstructured_service``
to avoid breaking compatibility while centralizing RAG-related imports.
"""

from src.services.unstructured_service import partition_document

__all__ = ["partition_document"]

