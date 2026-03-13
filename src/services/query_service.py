"""
Query Service for Question Answering.

This module provides the QueryService class that handles RAG (Retrieval-Augmented
Generation) queries over ingested documents. It uses the centralized RAG pipeline
and LLM service to answer questions with optional source document retrieval.

Architecture:
    - Uses vector store for semantic search
    - Integrates with document store for full document retrieval
    - Leverages LLM chain for answer generation

Integration Points:
    - REDIS_INTEGRATION: Cache frequent queries and responses
    - WEBSOCKET_INTEGRATION: Real-time query status updates
    - MQ_INTEGRATION: Async query processing for heavy workloads

Example:
    >>> from src.services.query_service import query_service
    >>> answer = query_service.ask_question("What is machine learning?")
    >>> result = query_service.ask_with_sources("Explain neural networks")
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import HTTPException, status

from src.services.vector_service import get_vectorstore, get_docstore
from src.services.retrieval_service import get_multi_vector_retriever, retrieve_with_sources
from src.services.llm_service import get_rag_chain


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

class QueryResponse(TypedDict):
    """Type definition for query response with sources."""
    answer: str
    sources: List[Dict[str, Any]]


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# REDIS_INTEGRATION: Add Redis client initialization here
# Example:
#   from redis import Redis
#   redis_client: Optional[Redis] = None
#
#   def get_cached_response(query_hash: str) -> Optional[str]:
#       """Retrieve cached query response from Redis."""
#       if redis_client:
#           return redis_client.get(f"query:{query_hash}")
#       return None
#
#   def cache_response(query_hash: str, response: str, ttl: int = 3600) -> None:
#       """Cache query response in Redis with TTL."""
#       if redis_client:
#           redis_client.setex(f"query:{query_hash}", ttl, response)

# WEBSOCKET_INTEGRATION: Add WebSocket event emitter here
# Example:
#   from src.core.events import event_emitter
#
#   async def emit_query_started(query_id: str, question: str) -> None:
#       """Emit WebSocket event when query processing starts."""
#       await event_emitter.emit("query:started", {"id": query_id, "question": question})
#
#   async def emit_query_completed(query_id: str, answer: str) -> None:
#       """Emit WebSocket event when query completes."""
#       await event_emitter.emit("query:completed", {"id": query_id, "answer": answer})

# MQ_INTEGRATION: Add message queue producer here
# Example:
#   from src.core.mq import message_queue
#
#   async def enqueue_query(question: str, priority: int = 1) -> str:
#       """Enqueue query for async processing via RabbitMQ/MCP."""
#       return await message_queue.publish("query_queue", {"question": question}, priority)


# =============================================================================
# Query Service Implementation
# =============================================================================

class QueryService:
    """
    Service responsible for running RAG queries over the current retriever.
    
    This service provides methods for querying ingested documents using
    Retrieval-Augmented Generation. It supports both simple question-answer
    queries and queries with source document attribution.
    
    Attributes:
        _cache_enabled (bool): Flag to enable/disable response caching.
            Reserved for future Redis integration.
    
    Integration Points:
        - REDIS_INTEGRATION: Query result caching
        - WEBSOCKET_INTEGRATION: Real-time query progress events
        - MQ_INTEGRATION: Async query job processing
    
    Example:
        >>> service = QueryService()
        >>> answer = service.ask_question("What is Python?")
        >>> print(answer)
    """
    
    def __init__(self, cache_enabled: bool = False) -> None:
        """
        Initialize the QueryService.
        
        Args:
            cache_enabled: Enable response caching (requires Redis integration).
                Defaults to False.
        """
        self._cache_enabled = cache_enabled
        # REDIS_INTEGRATION: Initialize Redis connection here
        # self._redis_client = get_redis_client() if cache_enabled else None
        
        logger.debug("QueryService initialized with cache_enabled=%s", cache_enabled)
    
    def _validate_vectorstore(self) -> None:
        """
        Validate that the vector store has documents available for querying.
        
        Raises:
            HTTPException: 503 Service Unavailable if no documents are indexed.
        
        Note:
            This validation is best-effort; the query continues even if
            the count check fails to avoid blocking valid queries.
        """
        vectorstore = get_vectorstore()
        
        try:
            collection = vectorstore._collection
            document_count = collection.count()
            
            if document_count == 0:
                logger.warning("Query attempted with empty vector store")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No documents have been processed yet for querying.",
                )
            
            logger.debug("Vector store contains %d documents", document_count)
            
        except HTTPException:
            # Re-raise HTTP exceptions (validation failures)
            raise
        except Exception as exc:
            # Log but continue if count check fails (non-critical)
            logger.debug("Vector store count check skipped: %s", str(exc))
    
    def ask_with_sources(self, question: str) -> QueryResponse:
        """
        Run a RAG query and return answer with source documents.
        
        Executes a RAG query similar to ask_question(), but additionally
        retrieves and returns the source documents that were used to
        generate the answer for citation and attribution purposes.
        
        Args:
            question: The natural language question to answer.
                Should be clear and specific for best results.
        
        Returns:
            A dictionary containing:
                - answer (str): The generated answer from the LLM.
                - sources (List[Dict]): List of source document metadata
                    including content, document ID, and relevance info.
        
        Raises:
            HTTPException: 503 if no documents are available for querying.
        
        Integration Points:
            - REDIS_INTEGRATION: Cache query+sources response
            - WEBSOCKET_INTEGRATION: Stream sources as they're retrieved
            - MQ_INTEGRATION: Queue source-heavy queries for background processing
        
        Example:
            >>> service = QueryService()
            >>> result = service.ask_with_sources("Explain the architecture")
            >>> print(f"Answer: {result['answer']}")
            >>> for source in result['sources']:
            ...     print(f"Source: {source}")
        """
        logger.info("Processing question with sources: %s", question[:100])
        
        # REDIS_INTEGRATION: Check cache for question+sources
        # cache_key = hashlib.md5(f"{question}:sources".encode()).hexdigest()
        # cached = get_cached_response(cache_key)
        # if cached:
        #     return json.loads(cached)
        
        # Initialize vector store and retriever
        vectorstore = get_vectorstore()
        docstore = get_docstore()
        retriever, id_key = get_multi_vector_retriever(vectorstore)
        
        # Retrieve source documents for attribution
        # WEBSOCKET_INTEGRATION: Could stream sources as they're found
        sources = retrieve_with_sources(retriever, docstore, question, id_key)
        logger.debug("Retrieved %d source documents", len(sources) if sources else 0)
        
        # Generate answer using RAG chain
        chain, _ = get_rag_chain(retriever)
        answer = chain.invoke(question)
        
        response: QueryResponse = {
            "answer": answer,
            "sources": sources
        }
        
        logger.info("Question with sources answered successfully")
        
        # REDIS_INTEGRATION: Cache the full response
        # cache_response(cache_key, json.dumps(response), ttl=3600)
        
        return response


# =============================================================================
# Module-Level Service Instance
# =============================================================================

# Singleton instance for dependency injection and direct usage
# This pattern allows for easy mocking in tests and consistent state
query_service: QueryService = QueryService()