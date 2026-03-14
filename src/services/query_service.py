"""Query service for RAG question answering."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypedDict

from src.core.exceptions import VectorStoreError
from src.services.rag_chain import get_rag_chain
from src.services.retrieval_service import get_multi_vector_retriever
from src.services.vector_service import get_docstore, get_vectorstore

logger = logging.getLogger(__name__)


class QueryResponse(TypedDict):
    answer: str
    sources: List[Dict[str, Any]]


class QueryService:
    """Service for running RAG queries over ingested documents."""

    def _validate_vectorstore(self) -> None:
        vectorstore = get_vectorstore()
        try:
            if vectorstore._collection.count() == 0:
                raise VectorStoreError("No documents have been processed yet for querying.")
        except VectorStoreError:
            raise
        except Exception as exc:
            logger.debug("Vector store count check skipped: %s", str(exc))

    def ask_with_sources(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> QueryResponse:
        """Run a RAG query and return the answer with source documents.

        Fix #1: uses chain_with_sources — retrieval happens once and the
        sources returned are exactly the documents the LLM received.
        """
        logger.info("Processing question: %s", question[:100])

        self._validate_vectorstore()

        vectorstore = get_vectorstore()
        docstore = get_docstore()
        retriever, id_key = get_multi_vector_retriever(vectorstore)

        _, chain_with_sources = get_rag_chain(retriever, chat_history=chat_history)
        result = chain_with_sources.invoke(question)

        answer = result["response"]

        # Sources come from the same retrieval the LLM used — no second round-trip
        sources: List[Dict[str, Any]] = []
        for doc in result["context"].get("texts", []):
            doc_id = doc.metadata.get(id_key) if hasattr(doc, "metadata") else None
            original = docstore.get(doc_id) if doc_id else None
            sources.append(
                {
                    "summary": doc.page_content if hasattr(doc, "page_content") else str(doc),
                    "original": original,
                    "type": doc.metadata.get("type", "text") if hasattr(doc, "metadata") else "text",
                    "doc_id": doc_id,
                }
            )

        return {"answer": answer, "sources": sources}


query_service: QueryService = QueryService()
