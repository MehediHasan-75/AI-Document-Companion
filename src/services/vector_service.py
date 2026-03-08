"""
Vector Store Service for Document Embeddings and Storage.

This module provides unified access to:
- Chroma vector store for semantic document search
- Simple document store for original content retrieval (key-value)

The vector store holds document embeddings (summaries) for similarity search,
while the document store maintains original content (text, tables, images)
for retrieval after matching.

Architecture:
    - Chroma DB for vector storage with persistence
    - HuggingFace embeddings (all-MiniLM-L6-v2) for dense representations
    - SimpleDocStore for key-value original content storage

Integration Points:
    - REDIS_INTEGRATION: Use Redis as distributed cache layer
    - WEBSOCKET_INTEGRATION: Real-time index status updates
    - MQ_INTEGRATION: Async document indexing pipeline

Configuration:
    - CHROMA_PERSIST_DIR: Directory for Chroma persistence (default: ./chroma_db)
    - DOCSTORE_PATH: Path for document store JSON (default: ./docstore.json)
    - EMBEDDING_MODEL: HuggingFace model name (default: all-MiniLM-L6-v2)

Example:
    >>> from src.services.vector_service import get_vectorstore, get_docstore
    >>> vectorstore = get_vectorstore()
    >>> docstore = get_docstore()
    >>> docstore.mset([("doc1", "Original content...")])
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)

# Storage Configuration Constants
# NOTE: Consider moving to environment variables or settings module for production
DEFAULT_CHROMA_PERSIST_DIR: str = "./chroma_db"
DEFAULT_DOCSTORE_PATH: str = "./docstore.json"
EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
COLLECTION_NAME: str = "document_summaries"

# Singleton instances for persistence across requests
_vectorstore: Optional[Chroma] = None
_docstore: Optional["SimpleDocStore"] = None


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# REDIS_INTEGRATION: Distributed caching layer
# Example:
#   class RedisDocStore:
#       """Redis-backed document store for distributed deployments."""
#       def __init__(self, redis_client):
#           self.redis = redis_client
#           self.prefix = "docstore:"
#
#       def mset(self, items: List[Tuple[str, Any]]) -> None:
#           pipeline = self.redis.pipeline()
#           for doc_id, content in items:
#               pipeline.set(f"{self.prefix}{doc_id}", json.dumps(content))
#           pipeline.execute()
#
#       def get(self, doc_id: str) -> Optional[Any]:
#           data = self.redis.get(f"{self.prefix}{doc_id}")
#           return json.loads(data) if data else None

# WEBSOCKET_INTEGRATION: Real-time indexing status
# Example:
#   async def emit_index_progress(doc_count: int, total: int) -> None:
#       """Emit indexing progress via WebSocket."""
#       await event_emitter.emit("index:progress", {
#           "current": doc_count, "total": total,
#           "percentage": int((doc_count / total) * 100)
#       })

# MQ_INTEGRATION: Async indexing pipeline
# Example:
#   async def enqueue_for_indexing(documents: List[str]) -> str:
#       """Queue documents for background indexing."""
#       job_id = str(uuid.uuid4())
#       await message_queue.publish("indexing_queue", {
#           "job_id": job_id, "documents": documents
#       })
#       return job_id


# =============================================================================
# Simple Document Store Implementation
# =============================================================================

class SimpleDocStore:
    """
    Simple key-value document store for original content (text, tables, images).
    
    This class provides a lightweight, JSON-persisted key-value store for
    storing original document content that can be retrieved by ID after
    vector similarity search returns matching summaries.
    
    Attributes:
        store: Internal dictionary holding document ID -> content mappings.
        persist_path: Optional path for JSON persistence.
    
    Integration Points:
        - REDIS_INTEGRATION: Replace with RedisDocStore for distributed caching
        - MQ_INTEGRATION: Emit indexing events when documents are added
    
    Example:
        >>> docstore = SimpleDocStore(persist_path="./docs.json")
        >>> docstore.mset([("doc1", "Hello"), ("doc2", "World")])
        >>> print(docstore.get("doc1"))  # "Hello"
    
    Note:
        For production deployments with multiple workers, consider using
        Redis-backed storage to ensure consistency across instances.
    """
    
    def __init__(self, persist_path: Optional[str] = None) -> None:
        """
        Initialize the SimpleDocStore.
        
        Args:
            persist_path: Optional file path for JSON persistence.
                If provided and file exists, loads existing data.
                If None, operates as in-memory only store.
        """
        self.store: Dict[str, Any] = {}
        self.persist_path: Optional[str] = persist_path
        
        if persist_path and os.path.exists(persist_path):
            self._load()
            logger.debug("Loaded %d documents from %s", len(self.store), persist_path)
        else:
            logger.debug("Initialized empty docstore (persist_path=%s)", persist_path)
    
    def mset(self, items: List[tuple]) -> None:
        """
        Set multiple documents at once.
        
        Args:
            items: List of (doc_id, content) tuples to store.
                Content can be any type; non-serializable objects
                are converted to strings.
        
        Note:
            Objects with a 'text' attribute are automatically
            converted to string representation for serialization.
        
        Integration Points:
            - MQ_INTEGRATION: Emit document:indexed events after storage
        """
        for doc_id, content in items:
            # Convert non-serializable objects to string
            if hasattr(content, 'text'):
                self.store[doc_id] = str(content)
            else:
                self.store[doc_id] = content
        
        self._save()
        logger.debug("Stored %d documents", len(items))
    
    def get(self, doc_id: str) -> Optional[Any]:
        """
        Get a single document by ID.
        
        Args:
            doc_id: The unique identifier of the document to retrieve.
        
        Returns:
            The document content if found, None otherwise.
        
        Integration Points:
            - REDIS_INTEGRATION: Check Redis cache first, fallback to local
        """
        return self.store.get(doc_id)
    
    def mget(self, doc_ids: List[str]) -> List[Optional[Any]]:
        """
        Get multiple documents by IDs.
        
        Args:
            doc_ids: List of document IDs to retrieve.
        
        Returns:
            List of document contents in the same order as doc_ids.
            Returns None for any ID not found in the store.
        
        Integration Points:
            - REDIS_INTEGRATION: Batch fetch from Redis using MGET
        """
        return [self.store.get(doc_id) for doc_id in doc_ids]
    
    def _save(self) -> None:
        """
        Persist the store to JSON file.
        
        Creates parent directories if they don't exist.
        Silently skips if no persist_path is configured.
        """
        if self.persist_path:
            Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(self.store, f, ensure_ascii=False, indent=2)
            logger.debug("Persisted docstore to %s", self.persist_path)
    
    def _load(self) -> None:
        """
        Load the store from JSON file.
        
        Only called if persist_path exists during initialization.
        """
        if self.persist_path and os.path.exists(self.persist_path):
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                self.store = json.load(f)


# =============================================================================
# Vector Store Factory Functions
# =============================================================================

def get_vectorstore(persist_directory: str = DEFAULT_CHROMA_PERSIST_DIR) -> Chroma:
    """
    Return a Chroma vector store singleton for storing summaries with embeddings.
    
    This function provides a singleton Chroma instance configured with
    HuggingFace embeddings for semantic similarity search over document
    summaries.
    
    Args:
        persist_directory: Directory path for Chroma database persistence.
            Defaults to "./chroma_db".
    
    Returns:
        Chroma vector store instance with configured embeddings.
    
    Integration Points:
        - REDIS_INTEGRATION: Could add Redis caching layer for embeddings
        - WEBSOCKET_INTEGRATION: Emit vectorstore:ready event on initialization
    
    Example:
        >>> vectorstore = get_vectorstore()
        >>> vectorstore.add_documents([Document(page_content="Hello")])
    
    Note:
        Uses singleton pattern - repeated calls return the same instance.
        To force reinitialization, set _vectorstore to None first.
    """
    global _vectorstore
    
    if _vectorstore is None:
        logger.info("Initializing Chroma vector store at %s", persist_directory)
        
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        
        _vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=persist_directory
        )
        
        logger.info("Vector store initialized with collection '%s'", COLLECTION_NAME)
        
        # WEBSOCKET_INTEGRATION: Emit ready event
        # await emit_vectorstore_ready(persist_directory)
    
    return _vectorstore


def get_docstore(persist_path: str = DEFAULT_DOCSTORE_PATH) -> SimpleDocStore:
    """
    Return a SimpleDocStore singleton for storing original content.
    
    This function provides a singleton document store for storing and
    retrieving original document content (text, tables, images) by ID.
    
    Args:
        persist_path: File path for JSON persistence of the document store.
            Defaults to "./docstore.json".
    
    Returns:
        SimpleDocStore instance for key-value document storage.
    
    Integration Points:
        - REDIS_INTEGRATION: Return RedisDocStore for distributed deployments
    
    Example:
        >>> docstore = get_docstore()
        >>> docstore.mset([("id1", "content1")])
        >>> print(docstore.get("id1"))
    
    Note:
        Uses singleton pattern - repeated calls return the same instance.
        To force reinitialization, set _docstore to None first.
    """
    global _docstore
    
    if _docstore is None:
        logger.info("Initializing document store at %s", persist_path)
        _docstore = SimpleDocStore(persist_path=persist_path)
        
        # REDIS_INTEGRATION: Use Redis-backed store instead
        # if redis_enabled:
        #     _docstore = RedisDocStore(redis_client)
    
    return _docstore
