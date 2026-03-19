"""Streaming RAG service.

Streams LLM responses token-by-token via SSE with conversation persistence.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List

from langchain_core.runnables import RunnableLambda
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session

from src.config import settings
from src.config.constants import DEFAULT_ID_KEY, QA_TEMPERATURE
from src.models.message import MessageRole
from src.services.conversation_service import conversation_service
from src.services.rag_chain import build_prompt, parse_docs, resolve_originals
from src.services.retrieval_service import get_multi_vector_retriever
from src.services.vector_service import get_vectorstore

logger = logging.getLogger(__name__)


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
) -> AsyncGenerator[str, None]:
    """Stream RAG response token-by-token as SSE events.

    Protocol:
      {"type": "delta", "content": "<token>"}      — each LLM token
      {"type": "complete", "content": "<full>",
       "conversation_id": "...", "sources": [...]}  — final message
      {"type": "error", "content": "..."}           — on failure
    """
    # Validate conversation ownership
    conversation_service.get_conversation(db, conversation_id, user_id)

    # Load chat history and save user message
    history = conversation_service.get_history(db, conversation_id, user_id)
    conversation_service.add_message(
        db, conversation_id, MessageRole.USER, question, user_id
    )

    full_response = ""
    sources: List[Dict[str, Any]] = []

    try:
        # Step 1: Retrieve and process context (non-streaming)
        vectorstore = get_vectorstore()
        retriever, _ = get_multi_vector_retriever(vectorstore, user_id=user_id)
        retrieval_chain = (
            retriever
            | RunnableLambda(resolve_originals)
            | RunnableLambda(parse_docs)
        )
        context = retrieval_chain.invoke(question)
        sources = _extract_sources(context)

        # Step 2: Build prompt with context + history
        messages = build_prompt({
            "context": context,
            "question": question,
            "chat_history": history,
        })

        # Step 3: Stream LLM response token-by-token
        llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_HOST,
            temperature=QA_TEMPERATURE,
        )
        async for chunk in llm.astream(messages):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            if token:
                full_response += token
                delta = json.dumps({"type": "delta", "content": token})
                yield f"data: {delta}\n\n"

    except Exception as e:
        logger.error("Streaming error: %s", e, exc_info=True)
        error_msg = str(e)
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        if not full_response:
            full_response = f"Error: {error_msg}"

    # Save assistant response with sources
    if full_response:
        conversation_service.add_message(
            db, conversation_id, MessageRole.ASSISTANT, full_response,
            user_id, sources=sources,
        )

    # Final completion event
    complete = json.dumps({
        "type": "complete",
        "content": full_response,
        "conversation_id": conversation_id,
        "sources": sources,
    })
    yield f"data: {complete}\n\n"
