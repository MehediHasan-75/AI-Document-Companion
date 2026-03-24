"""Streaming RAG service.

Streams the full RAG pipeline via SSE using astream_events():
  status events for each pipeline step, delta events for LLM tokens.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from src.config.constants import DEFAULT_ID_KEY
from src.models.message import MessageRole
from src.services.conversation_service import conversation_service
from src.services.rag_chain import build_rag_chain
from src.services.retrieval_service import get_multi_vector_retriever
from src.services.vector_service import get_vectorstore

logger = logging.getLogger(__name__)

_STEP_LABELS = {
    "resolve_originals": "Resolving original content...",
    "parse_docs": "Parsing document types...",
    "build_prompt": "Building prompt...",
}


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _extract_sources(context: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Build source metadata from retrieved context documents."""
    sources: List[Dict[str, Any]] = []
    for doc in context.get("texts", []):
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        doc_id = metadata.get(DEFAULT_ID_KEY)
        summary = metadata.get("summary", doc.page_content if hasattr(doc, "page_content") else str(doc))
        original = doc.page_content if hasattr(doc, "page_content") else str(doc)
        sources.append({
            "summary": summary,
            "original": original,
            "type": metadata.get("type", "text"),
            "doc_id": doc_id,
        })
    return sources


async def stream_chat_response(
    question: str,
    user_id: str,
    db: Session,
    conversation_id: str,
    doc_ids: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """Stream the full RAG pipeline as SSE events via astream_events().

    Protocol:
      {"type": "status", "content": "<step label>"}   — pipeline step started
      {"type": "thinking", "content": "<token>"}       — reasoning token (from reasoning_content)
      {"type": "delta", "content": "<token>"}          — each LLM token
      {"type": "complete", "content": "<full>",
       "conversation_id": "...", "sources": [...]}     — final message
      {"type": "error", "content": "..."}              — on failure
    """
    conversation_service.get_conversation(db, conversation_id, user_id)

    history = conversation_service.get_history(db, conversation_id, user_id)
    conversation_service.add_message(
        db, conversation_id, MessageRole.USER, question, user_id
    )

    full_response = ""
    sources: List[Dict[str, Any]] = []

    try:
        vectorstore = get_vectorstore()
        retriever, _ = get_multi_vector_retriever(vectorstore, user_id=user_id, doc_ids=doc_ids)
        chain = build_rag_chain(retriever, question, history)

        async for event in chain.astream_events(question, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            if kind == "on_retriever_start":
                yield _sse({"type": "status", "content": "Searching documents..."})

            elif kind == "on_chain_start" and name in _STEP_LABELS:
                yield _sse({"type": "status", "content": _STEP_LABELS[name]})

            elif kind == "on_chat_model_start":
                yield _sse({"type": "status", "content": "Generating response..."})

            elif kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]

                reasoning = chunk.additional_kwargs.get("reasoning_content")
                if reasoning:
                    yield _sse({"type": "thinking", "content": reasoning})

                token = chunk.content
                if token:
                    full_response += token
                    yield _sse({"type": "delta", "content": token})

            elif kind == "on_chain_end" and name == "parse_docs":
                sources = _extract_sources(event["data"]["output"])

    except Exception as e:
        logger.error("Streaming error: %s", e, exc_info=True)
        error_msg = str(e)
        yield _sse({"type": "error", "content": error_msg})
        if not full_response:
            full_response = f"Error: {error_msg}"

    if full_response:
        conversation_service.add_message(
            db, conversation_id, MessageRole.ASSISTANT, full_response,
            user_id, sources=sources,
        )

    yield _sse({
        "type": "complete",
        "content": full_response,
        "conversation_id": conversation_id,
        "sources": sources,
    })
