"""
Multi-Vector Retrieval Service for RAG Pipeline.

This module provides retrieval helpers for the multi-vector RAG architecture:
- Summaries stored in VectorDB for semantic search
- Original content stored in DocStore for retrieval by ID

The retrieval flow:
1. User query -> Vector similarity search on summaries
2. Get doc_ids from matched summaries
3. Retrieve original content from DocStore using doc_ids

Architecture:
    - VectorDB holds embeddings of document summaries
    - DocStore holds original content (text, tables, images)
    - Retriever bridges both stores for unified access

Integration Points:
    - REDIS_INTEGRATION: Cache retrieval results
    - WEBSOCKET_INTEGRATION: Stream retrieval progress
    - MQ_INTEGRATION: Async retrieval for large result sets

Example:
    >>> from src.services.retrieval_service import get_multi_vector_retriever
    >>> retriever, id_key = get_multi_vector_retriever(vectorstore)
    >>> results = retrieve_with_sources(retriever, docstore, "What is AI?", id_key)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langchain_core.documents import Document


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)

# Retrieval Configuration
DEFAULT_SEARCH_K: int = 5
DEFAULT_SEARCH_TYPE: str = "similarity"
DEFAULT_ID_KEY: str = "doc_id"


# =============================================================================
# Type Definitions
# =============================================================================

class SourceResult(TypedDict):
    """Type definition for a source document result."""
    summary: str
    original: Optional[str]
    type: str
    doc_id: Optional[str]


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# REDIS_INTEGRATION: Cache retrieval results
# Example:
#   def get_cached_retrieval(query_hash: str) -> Optional[List[SourceResult]]:
#       """Retrieve cached retrieval results from Redis."""
#       cached = redis_client.get(f"retrieval:{query_hash}")
#       return json.loads(cached) if cached else None
#
#   def cache_retrieval(query_hash: str, results: List[SourceResult], ttl: int = 1800) -> None:
#       """Cache retrieval results with 30-minute TTL."""
#       redis_client.setex(f"retrieval:{query_hash}", ttl, json.dumps(results))

# WEBSOCKET_INTEGRATION: Stream retrieval progress
# Example:
#   async def emit_retrieval_started(query: str) -> None:
#       """Emit WebSocket event when retrieval starts."""
#       await event_emitter.emit("retrieval:started", {"query": query})
#
#   async def emit_source_found(source: SourceResult, index: int, total: int) -> None:
#       """Stream each source as it's retrieved."""
#       await event_emitter.emit("retrieval:source", {
#           "source": source, "index": index, "total": total
#       })

# MQ_INTEGRATION: Async retrieval for batch processing
# Example:
#   async def enqueue_batch_retrieval(queries: List[str]) -> str:
#       """Queue multiple queries for batch retrieval."""
#       job_id = str(uuid.uuid4())
#       await message_queue.publish("retrieval_queue", {
#           "job_id": job_id, "queries": queries
#       })
#       return job_id


# =============================================================================
# Retriever Factory
# =============================================================================

def get_multi_vector_retriever(
    vectorstore: Any,
    search_type: str = DEFAULT_SEARCH_TYPE,
    search_k: int = DEFAULT_SEARCH_K
) -> Tuple[Any, str]:
    """
    Return a retriever from a vectorstore and a unique ID key for documents.
    
    Creates a retriever configured for similarity search over document
    summaries. The retriever searches summaries and returns doc_ids that
    can be used to look up original content from the DocStore.
    
    Args:
        vectorstore: A LangChain-compatible vector store instance
            (e.g., Chroma) containing document summary embeddings.
        search_type: The type of search to perform. Options:
            - "similarity": Standard cosine similarity search
            - "mmr": Maximum Marginal Relevance for diversity
            Defaults to "similarity".
        search_k: Number of top results to retrieve. Defaults to 5.
    
    Returns:
        Tuple containing:
            - retriever: Configured retriever instance
            - id_key: The metadata key used for document IDs ("doc_id")
    
    Integration Points:
        - REDIS_INTEGRATION: Could add caching wrapper around retriever
        - WEBSOCKET_INTEGRATION: Wrap retriever to emit search events
    
    Example:
        >>> vectorstore = get_vectorstore()
        >>> retriever, id_key = get_multi_vector_retriever(vectorstore)
        >>> docs = retriever.invoke("What is machine learning?")
    
    Note:
        The id_key ("doc_id") must match the key used when adding documents
        via add_documents_to_retriever() to enable source lookup.
    """
    logger.debug(
        "Creating retriever with search_type=%s, k=%d",
        search_type, search_k
    )
    
    id_key = DEFAULT_ID_KEY
    
    retriever = vectorstore.as_retriever(
        search_type=search_type,
        search_kwargs={"k": search_k}
    )
    
    return retriever, id_key


# =============================================================================
# Document Indexing
# =============================================================================

def add_documents_to_retriever(
    vectorstore: Any,
    docstore: Any,
    texts: Optional[List[Any]] = None,
    text_summaries: Optional[List[str]] = None,
    tables: Optional[List[Any]] = None,
    table_summaries: Optional[List[str]] = None,
    images: Optional[List[str]] = None,
    image_summaries: Optional[List[str]] = None,
    id_key: str = DEFAULT_ID_KEY,
) -> Dict[str, int]:
    """
    Add documents to the multi-vector retriever system.
    
    Indexes documents by storing:
    - Summaries in VectorDB (with embeddings) for semantic search
    - Originals in DocStore (key-value) for retrieval by doc_id
    
    Args:
        vectorstore: Vector store instance for summary embeddings.
        docstore: Document store instance for original content.
        texts: Optional list of text chunks to index.
        text_summaries: Summaries corresponding to texts (same length).
        tables: Optional list of table elements to index.
        table_summaries: Summaries corresponding to tables (same length).
        images: Optional list of base64-encoded images to index.
        image_summaries: Summaries corresponding to images (same length).
        id_key: Metadata key for document IDs. Defaults to "doc_id".
    
    Returns:
        Dictionary with counts of indexed items by type:
            {"texts": n, "tables": n, "images": n}
    
    Raises:
        ValueError: If summaries and content lists have mismatched lengths.
    
    Integration Points:
        - WEBSOCKET_INTEGRATION: Emit progress events during indexing
        - MQ_INTEGRATION: Could be called from async job processor
    
    Example:
        >>> vectorstore = get_vectorstore()
        >>> docstore = get_docstore()
        >>> counts = add_documents_to_retriever(
        ...     vectorstore, docstore,
        ...     texts=["Hello world"], text_summaries=["Greeting text"]
        ... )
        >>> print(counts)  # {"texts": 1, "tables": 0, "images": 0}
    
    Note:
        Each content type (texts, tables, images) must have a corresponding
        summaries list of the same length, or both should be None/empty.
    """
    counts = {"texts": 0, "tables": 0, "images": 0}
    
    # Add texts: summaries to vectorstore, originals to docstore
    if texts and text_summaries:
        if len(texts) != len(text_summaries):
            raise ValueError(
                f"Texts and summaries length mismatch: {len(texts)} vs {len(text_summaries)}"
            )
        
        text_ids = [str(uuid.uuid4()) for _ in texts]
        summary_docs = [
            Document(
                page_content=summary,
                metadata={id_key: text_ids[i], "type": "text"}
            )
            for i, summary in enumerate(text_summaries)
        ]
        vectorstore.add_documents(summary_docs)
        docstore.mset(list(zip(text_ids, [str(t) for t in texts])))
        
        counts["texts"] = len(texts)
        logger.info("Added %d text chunks", len(texts))
        
        # WEBSOCKET_INTEGRATION: Emit indexing progress
        # await emit_index_progress("text", len(texts))

    # Add tables: summaries to vectorstore, HTML to docstore
    if tables and table_summaries:
        if len(tables) != len(table_summaries):
            raise ValueError(
                f"Tables and summaries length mismatch: {len(tables)} vs {len(table_summaries)}"
            )
        
        table_ids = [str(uuid.uuid4()) for _ in tables]
        summary_docs = [
            Document(
                page_content=summary,
                metadata={id_key: table_ids[i], "type": "table"}
            )
            for i, summary in enumerate(table_summaries)
        ]
        vectorstore.add_documents(summary_docs)
        
        # Extract HTML content from table elements if available
        table_contents = [
            t.metadata.text_as_html if hasattr(t, 'metadata') else str(t)
            for t in tables
        ]
        docstore.mset(list(zip(table_ids, table_contents)))
        
        counts["tables"] = len(tables)
        logger.info("Added %d tables", len(tables))

    # Add images: summaries to vectorstore, base64 to docstore
    if images and image_summaries:
        if len(images) != len(image_summaries):
            raise ValueError(
                f"Images and summaries length mismatch: {len(images)} vs {len(image_summaries)}"
            )
        
        img_ids = [str(uuid.uuid4()) for _ in images]
        summary_docs = [
            Document(
                page_content=summary,
                metadata={id_key: img_ids[i], "type": "image"}
            )
            for i, summary in enumerate(image_summaries)
        ]
        vectorstore.add_documents(summary_docs)
        docstore.mset(list(zip(img_ids, images)))
        
        counts["images"] = len(images)
        logger.info("Added %d images", len(images))
    
    return counts


# =============================================================================
# Source Retrieval
# =============================================================================

def retrieve_with_sources(
    retriever: Any,
    docstore: Any,
    query: str,
    id_key: str = DEFAULT_ID_KEY
) -> List[SourceResult]:
    """
    Retrieve matching documents with their original source content.
    
    Executes the full retrieval flow:
    1. Search VectorDB for matching summaries
    2. Get doc_ids from matched summary metadata
    3. Retrieve original content from DocStore using doc_ids
    
    Args:
        retriever: Configured retriever instance from get_multi_vector_retriever.
        docstore: Document store containing original content.
        query: The search query string.
        id_key: Metadata key for document IDs. Defaults to "doc_id".
    
    Returns:
        List of SourceResult dictionaries, each containing:
            - summary: The matched summary text
            - original: Original content from docstore (or None if not found)
            - type: Content type ("text", "table", or "image")
            - doc_id: The unique document identifier
    
    Integration Points:
        - REDIS_INTEGRATION: Cache results by query hash
        - WEBSOCKET_INTEGRATION: Stream sources as they're retrieved
    
    Example:
        >>> retriever, id_key = get_multi_vector_retriever(vectorstore)
        >>> sources = retrieve_with_sources(
        ...     retriever, docstore, "What is deep learning?", id_key
        ... )
        >>> for source in sources:
        ...     print(f"Type: {source['type']}, Summary: {source['summary'][:50]}...")
    
    Note:
        The number of results depends on the retriever's k parameter
        configured in get_multi_vector_retriever().
    """
    logger.debug("Retrieving sources for query: %s", query[:100])
    
    # REDIS_INTEGRATION: Check cache first
    # cache_key = hashlib.md5(query.encode()).hexdigest()
    # cached = get_cached_retrieval(cache_key)
    # if cached:
    #     return cached
    
    # WEBSOCKET_INTEGRATION: Emit retrieval started
    # await emit_retrieval_started(query)
    
    # Get matching summaries from vector store
    matched_summaries = retriever.invoke(query)
    logger.debug("Found %d matching summaries", len(matched_summaries))
    
    # Extract doc_ids and retrieve originals
    results: List[SourceResult] = []
    
    for idx, doc in enumerate(matched_summaries):
        doc_id = doc.metadata.get(id_key)
        doc_type = doc.metadata.get("type", "text")
        original = docstore.get(doc_id) if doc_id else None
        
        result: SourceResult = {
            "summary": doc.page_content,
            "original": original,
            "type": doc_type,
            "doc_id": doc_id
        }
        results.append(result)
        
        # WEBSOCKET_INTEGRATION: Stream each source
        # await emit_source_found(result, idx, len(matched_summaries))
    
    # REDIS_INTEGRATION: Cache results
    # cache_retrieval(cache_key, results)
    
    logger.info("Retrieved %d sources for query", len(results))
    
    return results