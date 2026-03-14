"""Query controller for RAG question answering."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TypedDict

from src.services.query_service import query_service

logger = logging.getLogger(__name__)


class QueryWithSourcesResult(TypedDict):
    answer: str
    sources: List[Dict[str, Any]]


class QueryController:
    """Controller for RAG query operations."""

    def __init__(self) -> None:
        self.service = query_service

    def ask_with_sources(self, question: str) -> QueryWithSourcesResult:
        """Ask a question and return the answer with source documents."""
        logger.info("Processing query with sources: %s", question[:100])
        result = self.service.ask_with_sources(question)
        logger.info("Query answered with %d sources", len(result.get("sources", [])))
        return result


query_controller: QueryController = QueryController()
