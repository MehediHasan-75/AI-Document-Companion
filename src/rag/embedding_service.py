"""
Facade for embedding model helpers used in the RAG pipeline.

Delegates to ``src.services.embedding_service``.
"""

from src.services.embedding_service import get_openai_embeddings

__all__ = ["get_openai_embeddings"]

