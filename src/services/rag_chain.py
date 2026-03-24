"""RAG chain construction for question answering."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

from src.config.constants import DEFAULT_ID_KEY, MAX_CONTEXT_TOKENS, MAX_HISTORY_EXCHANGES
from src.config.prompts import RAG_SYSTEM_PROMPT
from src.services.vector_service import get_docstore

logger = logging.getLogger(__name__)


def resolve_originals(docs: List[Document]) -> List[Document]:
    """Replace summary content with original content from the docstore.

    The vector store contains LLM-generated summaries (used for retrieval),
    but the LLM should reason over the original full-fidelity content.
    Uses a dict-based lookup for clarity instead of fragile index tracking.
    """
    docstore = get_docstore()
    doc_ids = [doc.metadata.get(DEFAULT_ID_KEY) for doc in docs]
    valid_ids = [did for did in doc_ids if did]
    originals = docstore.mget(valid_ids)
    lookup = dict(zip(valid_ids, originals))

    resolved: List[Document] = []
    for doc in docs:
        doc_id = doc.metadata.get(DEFAULT_ID_KEY)
        original = lookup.get(doc_id) if doc_id else None
        if doc.metadata.get("type") == "image":
            # Parse stored JSON to get base64 URL and summary for LLM context
            metadata = {**doc.metadata}
            content = doc.page_content  # fallback: summary already in ChromaDB doc
            if original:
                try:
                    img_data = json.loads(original)
                    metadata["image_base64"] = img_data.get("base64")
                    content = img_data.get("summary", content)
                except (json.JSONDecodeError, AttributeError):
                    # Legacy entry: raw base64 string (pre-migration)
                    metadata["image_base64"] = f"data:image/jpeg;base64,{original}"
            resolved.append(Document(page_content=content, metadata=metadata))
        elif original:
            metadata = {**doc.metadata, "summary": doc.page_content}
            resolved.append(Document(page_content=original, metadata=metadata))
        else:
            resolved.append(doc)
    return resolved


def parse_docs(docs: List[Document]) -> Dict[str, List[Any]]:
    """Split retrieved documents into text documents (no multimodal path for text-only LLMs).

    Image chunks keep their LLM-generated summary as page_content (set by resolve_originals),
    so all docs are routed as text context.
    """
    return {"images": [], "texts": docs}


def _build_context_text(text_docs: List[Document]) -> str:
    """Build numbered source context within the token budget."""
    context_parts: List[str] = []
    token_count = 0
    for i, doc in enumerate(text_docs, 1):
        if not hasattr(doc, "page_content"):
            continue
        content = doc.page_content
        doc_tokens = len(content) // 4
        if token_count + doc_tokens > MAX_CONTEXT_TOKENS:
            break
        context_parts.append(f"[Source {i}]\n{content}")
        token_count += doc_tokens

    return "\n---\n".join(context_parts) if context_parts else "No relevant context found."


def _build_history_messages(chat_history: List[Dict[str, str]]) -> List[BaseMessage]:
    """Convert chat history dicts to LangChain message objects."""
    recent = chat_history[-(MAX_HISTORY_EXCHANGES * 2):]
    messages: List[BaseMessage] = []
    for msg in recent:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    return messages


def build_prompt(kwargs: Dict[str, Any]) -> List[BaseMessage]:
    """Build a multi-modal prompt from context documents, chat history, and user question."""
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]
    chat_history: List[Dict[str, str]] = kwargs.get("chat_history", [])

    context_text = _build_context_text(docs_by_type.get("texts", []))

    # System message with RAG rules and context
    system_content = f"{RAG_SYSTEM_PROMPT}\n\nContext:\n{context_text}"
    messages: List[BaseMessage] = [SystemMessage(content=system_content)]

    # Chat history as proper HumanMessage / AIMessage pairs
    if chat_history:
        messages.extend(_build_history_messages(chat_history))

    # User question (with optional images) as a HumanMessage
    question_content: List[Dict[str, Any]] = [
        {"type": "text", "text": f"<user_question>{user_question}</user_question>"}
    ]
    for image in docs_by_type.get("images", []):
        question_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"},
            }
        )

    messages.append(HumanMessage(content=question_content))

    return messages


def build_rag_chain(retriever: Any, question: str, history: List[Dict[str, Any]]) -> Any:
    """Build the full RAG LCEL chain for streaming via astream_events().

    Chain: retriever → resolve_originals → parse_docs → build_prompt → llm
    Each step is named so astream_events() can identify it by event["name"].
    """
    from src.services.llm_service import get_qa_llm

    return (
        retriever
        | RunnableLambda(resolve_originals).with_config(run_name="resolve_originals")
        | RunnableLambda(parse_docs).with_config(run_name="parse_docs")
        | RunnableLambda(lambda ctx: build_prompt({
            "context": ctx,
            "question": question,
            "chat_history": history,
        })).with_config(run_name="build_prompt")
        | get_qa_llm()
    )
