"""
Facade for LangChain MultiVectorRetriever helpers used in the RAG pipeline.

Delegates to ``src.services.retrival_service`` (note the legacy filename).
"""

from src.services.retrival_service import (
    get_multi_vector_retriever,
    add_documents_to_retriever,
)

__all__ = ["get_multi_vector_retriever", "add_documents_to_retriever"]

