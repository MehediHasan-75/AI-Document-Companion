"""
Facade for vector store helpers used in the RAG pipeline.

Delegates to ``src.services.vector_service`` which configures a persistent
Chroma instance backed by OpenAI embeddings.
"""

from src.services.vector_service import get_vectorstore, get_docstore

__all__ = ["get_vectorstore", "get_docstore"]

