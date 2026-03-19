"""Query service for RAG question answering."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypedDict

from src.services.rag_chain import get_rag_chain
from src.services.retrieval_service import get_multi_vector_retriever
from src.services.vector_service import get_docstore, get_vectorstore

logger = logging.getLogger(__name__)


class QueryResponse(TypedDict):
    answer: str
    sources: List[Dict[str, Any]]


class QueryService:
    """Service for running RAG queries over ingested documents."""

    def ask_with_sources(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
    ) -> QueryResponse:
        """Run a RAG query and return the answer with source documents.

        Uses chain_with_sources — retrieval happens once and the sources
        returned are exactly the documents the LLM received.
        """
        logger.info("Processing question: %s", question[:100])

        vectorstore = get_vectorstore()
        docstore = get_docstore()
        retriever, id_key = get_multi_vector_retriever(
            vectorstore, user_id=user_id
        )

        chain_with_sources = get_rag_chain(retriever, chat_history=chat_history)
        result = chain_with_sources.invoke(question)

        answer = result["response"]

        # Sources come from the same retrieval the LLM used — no second round-trip
        sources: List[Dict[str, Any]] = []
        for doc in result["context"].get("texts", []):
            metadata = doc.metadata if hasattr(doc, "metadata") else {}
            doc_id = metadata.get(id_key)
            summary = metadata.get("summary", doc.page_content if hasattr(doc, "page_content") else str(doc))
            original = doc.page_content if hasattr(doc, "page_content") else str(doc)
            sources.append(
                {
                    "summary": summary,
                    "original": original,
                    "type": metadata.get("type", "text"),
                    "doc_id": doc_id,
                }
            )

        return {"answer": answer, "sources": sources}


query_service: QueryService = QueryService()
