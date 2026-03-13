"""
Query Controller Module.

Handles HTTP-facing orchestration for RAG question answering,
providing a clean interface between routes and the query service layer.

Architecture:
    - Controller pattern separating HTTP concerns from business logic
    - Delegates to QueryService for actual RAG operations
    - Returns standardized response structures

Integration Points:
    - WEBSOCKET_INTEGRATION: Stream query responses in real-time
    - REDIS_INTEGRATION: Cache frequent query responses
    - MQ_INTEGRATION: Queue complex queries for async processing

Example:
    >>> from src.controllers.query_controller import query_controller
    >>> result = query_controller.ask("What is machine learning?")
    >>> print(result["answer"])
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TypedDict

from src.services.query_service import query_service


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

class QueryResult(TypedDict):
    """Type definition for query response."""
    answer: str


class QueryWithSourcesResult(TypedDict):
    """Type definition for query response with sources."""
    answer: str
    sources: List[Dict[str, Any]]


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# WEBSOCKET_INTEGRATION: Stream responses
# Example:
#   async def stream_query_response(question: str, websocket) -> None:
#       async for token in query_service.ask_stream(question):
#           await websocket.send_json({"type": "token", "content": token})

# REDIS_INTEGRATION: Cache responses
# Example:
#   def get_cached_answer(question_hash: str) -> Optional[str]:
#       return redis_client.get(f"query:{question_hash}")
#
#   def cache_answer(question_hash: str, answer: str) -> None:
#       redis_client.setex(f"query:{question_hash}", 3600, answer)

# MQ_INTEGRATION: Async query processing
# Example:
#   async def enqueue_query(question: str) -> str:
#       job_id = str(uuid.uuid4())
#       await message_queue.publish("query_queue", {
#           "job_id": job_id, "question": question
#       })
#       return job_id


# =============================================================================
# Query Controller Implementation
# =============================================================================

class QueryController:
    """
    Controller for RAG query operations.
    
    Provides HTTP-facing methods for querying documents using the
    RAG pipeline. Handles query formatting and response transformation.
    
    Attributes:
        service: QueryService instance for RAG operations.
    
    Integration Points:
        - WEBSOCKET_INTEGRATION: Stream responses token by token
        - REDIS_INTEGRATION: Cache frequent query responses
        - MQ_INTEGRATION: Queue heavy queries for background processing
    
    Example:
        >>> controller = QueryController()
        >>> result = controller.ask("Explain the architecture")
        >>> print(result["answer"])
    """

    def __init__(self) -> None:
        """
        Initialize the QueryController.
        
        Sets up the connection to the QueryService singleton.
        """
        self.service = query_service
        logger.debug("QueryController initialized")

    # -------------------------------------------------------------------------
    # Query Operations
    # -------------------------------------------------------------------------

    def ask(self, question: str) -> QueryResult:
        """
        Ask a question over the ingested documents.
        
        Executes a RAG query using the configured retriever and LLM
        to generate an answer based on document content.
        
        Args:
            question: Natural language question to answer.
                Should be clear and specific for best results.
        
        Returns:
            Dictionary containing:
                - answer: The generated answer string
        
        Raises:
            HTTPException: 503 if no documents have been processed.
        
        Integration Points:
            - REDIS_INTEGRATION: Check cache before querying
            - WEBSOCKET_INTEGRATION: Could use streaming variant
        
        Example:
            >>> result = query_controller.ask("What are the main features?")
            >>> print(result["answer"])
        """
        logger.info("Processing query: %s", question[:100])
        
        # REDIS_INTEGRATION: Check cache first
        # cache_key = hashlib.md5(question.encode()).hexdigest()
        # cached = get_cached_answer(cache_key)
        # if cached:
        #     return {"answer": cached}
        
        answer = self.service.ask_with_sources(question)
        
        logger.info("Query answered successfully")
        
        # REDIS_INTEGRATION: Cache the response
        # cache_answer(cache_key, answer)
        
        return {"answer": answer}

    # -------------------------------------------------------------------------

    def ask_with_sources(self, question: str) -> QueryWithSourcesResult:
        """
        Ask a question and return answer with source documents.
        
        Executes a RAG query similar to ask(), but additionally
        returns the source documents used to generate the answer
        for citation and attribution purposes.
        
        Args:
            question: Natural language question to answer.
        
        Returns:
            Dictionary containing:
                - answer: The generated answer string
                - sources: List of source document information
        
        Raises:
            HTTPException: 503 if no documents have been processed.
        
        Example:
            >>> result = query_controller.ask_with_sources(
            ...     "Explain the architecture"
            ... )
            >>> print(f"Answer: {result['answer']}")
            >>> for source in result['sources']:
            ...     print(f"Source: {source['type']}")
        """
        logger.info("Processing query with sources: %s", question[:100])
        
        result = self.service.ask_with_sources(question)
        
        logger.info(
            "Query answered with %d sources",
            len(result.get("sources", []))
        )
        
        return result


# =============================================================================
# Module-Level Controller Instance
# =============================================================================

# Singleton instance for dependency injection and direct usage
query_controller: QueryController = QueryController()

