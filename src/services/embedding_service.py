"""
Embedding Service for Vector Representations.

This module provides factory functions for creating embedding models
used in the RAG pipeline for document vectorization and similarity search.

Supported Providers:
    - OpenAI Embeddings (text-embedding-ada-002, text-embedding-3-small, etc.)
    - HuggingFace Embeddings (used in vector_service.py)

Architecture:
    - Factory pattern for embedding model instantiation
    - Provider-agnostic interface for easy swapping
    - Configuration via environment variables

Integration Points:
    - REDIS_INTEGRATION: Cache computed embeddings
    - MQ_INTEGRATION: Batch embedding computation queue

Configuration:
    - OPENAI_API_KEY: Required for OpenAI embeddings
    - EMBEDDING_MODEL: Model name selection (optional)

Example:
    >>> from src.services.embedding_service import get_openai_embeddings
    >>> embeddings = get_openai_embeddings()
    >>> vector = embeddings.embed_query("What is machine learning?")
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_openai import OpenAIEmbeddings


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)

# Default embedding model
# Options: "text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"
DEFAULT_OPENAI_MODEL: str = "text-embedding-ada-002"


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# REDIS_INTEGRATION: Cache embeddings
# Example:
#   def get_cached_embedding(text_hash: str) -> Optional[List[float]]:
#       """Retrieve cached embedding vector from Redis."""
#       cached = redis_client.get(f"embedding:{text_hash}")
#       return json.loads(cached) if cached else None
#
#   def cache_embedding(text_hash: str, vector: List[float]) -> None:
#       """Cache embedding vector with TTL."""
#       redis_client.setex(f"embedding:{text_hash}", 86400, json.dumps(vector))

# MQ_INTEGRATION: Batch embedding queue
# Example:
#   async def enqueue_batch_embedding(texts: List[str]) -> str:
#       """Queue texts for batch embedding computation."""
#       job_id = str(uuid.uuid4())
#       await message_queue.publish("embedding_queue", {
#           "job_id": job_id, "texts": texts
#       })
#       return job_id


# =============================================================================
# Embedding Factory Functions
# =============================================================================

def get_openai_embeddings(
    model: Optional[str] = None,
    **kwargs
) -> OpenAIEmbeddings:
    """
    Create and return an OpenAI embeddings instance.
    
    Factory function that creates a configured OpenAIEmbeddings object
    for computing vector representations of text. Used for document
    embedding and query embedding in the RAG pipeline.
    
    Args:
        model: OpenAI embedding model name. Options:
            - "text-embedding-ada-002" (default, legacy)
            - "text-embedding-3-small" (faster, cheaper)
            - "text-embedding-3-large" (higher quality)
            If None, uses DEFAULT_OPENAI_MODEL.
        **kwargs: Additional arguments passed to OpenAIEmbeddings.
            Useful for setting custom API keys, base URLs, etc.
    
    Returns:
        Configured OpenAIEmbeddings instance ready for use.
    
    Integration Points:
        - REDIS_INTEGRATION: Wrap with caching layer for repeated texts
    
    Example:
        >>> embeddings = get_openai_embeddings()
        >>> vector = embeddings.embed_query("Hello world")
        >>> print(f"Vector dimension: {len(vector)}")
        
        >>> # Use newer model
        >>> embeddings_v3 = get_openai_embeddings(model="text-embedding-3-small")
    
    Note:
        Requires OPENAI_API_KEY environment variable to be set.
        For local embeddings, see get_huggingface_embeddings() in vector_service.py.
    """
    selected_model = model or DEFAULT_OPENAI_MODEL
    
    logger.debug("Creating OpenAI embeddings with model: %s", selected_model)
    
    return OpenAIEmbeddings(model=selected_model, **kwargs)
