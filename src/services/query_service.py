"""Query service for RAG question answering."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypedDict

from src.core.exceptions import VectorStoreError
from src.services.vector_service import get_vectorstore, get_docstore
from src.services.retrieval_service import get_multi_vector_retriever, retrieve_with_sources
from src.services.rag_chain import get_rag_chain

logger = logging.getLogger(__name__)


class QueryResponse(TypedDict):
    answer: str
    sources: List[Dict[str, Any]]


class QueryService:
    """Service for running RAG queries over ingested documents."""

    def _validate_vectorstore(self) -> None:
        """Raise if the vector store has no documents."""
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

        If chat_history is provided (list of {"role", "content"} dicts),
        previous conversation turns are included in the LLM prompt for
        context-aware follow-up answers.
        """
        logger.info("Processing question with sources: %s", question[:100])

        vectorstore = get_vectorstore()
        docstore = get_docstore()
        retriever, id_key = get_multi_vector_retriever(vectorstore)

        sources = retrieve_with_sources(retriever, docstore, question, id_key)
        chain, _ = get_rag_chain(retriever, chat_history=chat_history)
        answer = chain.invoke(question)

        return {"answer": answer, "sources": sources}


query_service: QueryService = QueryService()
