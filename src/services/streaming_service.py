"""Streaming RAG service.

Streams the full RAG pipeline via SSE using astream_events():
  status events for each pipeline step, delta events for LLM tokens.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from src.config.constants import DEFAULT_ID_KEY
from src.models.message import MessageRole
from src.services.conversation_service import conversation_service
from src.services.rag_chain import build_rag_chain
from src.services.retrieval_service import get_multi_vector_retriever
from src.services.vector_service import get_vectorstore

logger = logging.getLogger(__name__)

# Characters that break Mermaid parsing when unquoted inside node labels.
_MERMAID_UNSAFE = re.compile(r'[.()\[\]{},:#%<>\\]')

# Reserved Mermaid structural keywords that must not appear as bare node labels.
_MERMAID_RESERVED = frozenset({
    'end', 'subgraph', 'graph', 'flowchart', 'sequenceDiagram',
    'classDiagram', 'stateDiagram', 'erDiagram',
})

# First line of a valid Mermaid diagram.
_DIAGRAM_DECL = re.compile(
    r'^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram|gantt|pie|gitGraph|mindmap|timeline)\b',
    re.MULTILINE | re.IGNORECASE,
)


def _heal_mermaid_block(code: str) -> str:
    """Heal a single Mermaid code string.

    Steps:
    1. Strip conversational filler before the diagram declaration.
    2. Quote unquoted node labels that contain unsafe characters or reserved keywords.
    Covers all three common bracket types: [] () {}.
    """
    # 1. Strip mixed content — any prose before the first diagram keyword.
    m = _DIAGRAM_DECL.search(code)
    if m:
        code = code[m.start():]

    # 2. Quote unsafe / reserved labels.
    def _maybe_quote(m: re.Match, open_b: str, close_b: str) -> str:
        node_id, label = m.group(1), m.group(2)
        if label.startswith('"') and label.endswith('"'):
            return m.group(0)  # already quoted — leave untouched
        has_unsafe = bool(_MERMAID_UNSAFE.search(label))
        is_reserved = label.strip().lower() in _MERMAID_RESERVED
        if has_unsafe or is_reserved:
            safe = label.replace('"', "'")  # escape any embedded double-quotes
            return f'{node_id}{open_b}"{safe}"{close_b}'
        return m.group(0)

    # Rectangular [label]
    code = re.sub(
        r'\b(\w+)\[([^"\]\[]+)\]',
        lambda m: _maybe_quote(m, '[', ']'),
        code,
    )
    # Round (label) — word boundary prevents matching --> arrows
    code = re.sub(
        r'\b(\w+)\(([^"\)\(]+)\)',
        lambda m: _maybe_quote(m, '(', ')'),
        code,
    )
    # Diamond / rhombus {label}
    code = re.sub(
        r'\b(\w+)\{([^"\}\{]+)\}',
        lambda m: _maybe_quote(m, '{', '}'),
        code,
    )

    return code


def _sanitize_mermaid(text: str) -> str:
    """Find and heal all Mermaid code blocks in *text*.

    Also auto-closes any truncated (unclosed) mermaid block left by a
    premature stream termination so Markdown parsers don't leak raw DSL.
    """
    def fix_block(m: re.Match) -> str:
        return f'```mermaid\n{_heal_mermaid_block(m.group(1))}```'

    healed = re.sub(r'```mermaid\n(.*?)```', fix_block, text, flags=re.DOTALL)

    # Auto-close a truncated block at the end of the response.
    last_open = healed.rfind('```mermaid')
    if last_open != -1 and '```' not in healed[last_open + len('```mermaid'):]:
        healed += '\n```'

    return healed


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
            "image_base64": metadata.get("image_base64"),
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

    full_response = _sanitize_mermaid(full_response)

    # Derive image list before persisting so sources are complete
    images = [s["image_base64"] for s in sources if s.get("type") == "image" and s.get("image_base64")]

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
        "images": images,
    })
