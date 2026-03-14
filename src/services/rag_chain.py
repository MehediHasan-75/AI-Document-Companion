"""RAG chain construction for question answering."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from src.services.llm_service import get_text_llm  # Fix #3: reuse singleton

logger = logging.getLogger(__name__)


def parse_docs(docs: List[Document]) -> Dict[str, List[Any]]:
    """Split retrieved documents into base64-encoded images and text documents.

    Fix #1: use the 'type' metadata field set during ingestion instead of
    attempting b64decode (which silently succeeds on many plain-text strings).
    """
    b64_images: List[str] = []
    text_docs: List[Document] = []

    for doc in docs:
        if doc.metadata.get("type") == "image":
            b64_images.append(doc.page_content)
        else:
            text_docs.append(doc)

    return {"images": b64_images, "texts": text_docs}


def build_prompt(kwargs: Dict[str, Any]) -> List[BaseMessage]:
    """Build a multi-modal prompt from context documents, chat history, and user question."""
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]
    chat_history: List[Dict[str, str]] = kwargs.get("chat_history", [])

    context_text = "".join(
        [doc.page_content for doc in docs_by_type.get("texts", []) if hasattr(doc, "page_content")]
    )

    history_section = ""
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role_label}: {msg['content']}")
        history_section = "\nConversation history:\n" + "\n".join(history_lines) + "\n"

    prompt_template = (
        f"Answer the question based only on the following context, "
        f"which can include text, tables, and the below image.\n"
        f"Context: {context_text}"
        f"{history_section}\n"
        f"Question: {user_question}"
    )

    prompt_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt_template}]

    for image in docs_by_type.get("images", []):
        prompt_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"},
            }
        )

    return [HumanMessage(content=prompt_content)]


def get_rag_chain(
    retriever: Any,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[Any, Any]:
    """Construct RAG chains for question answering (standard and with sources).

    chain_with_sources returns {context, question, chat_history, response}.
    Prefer it over chain: single retrieval, sources match exactly what the LLM saw.
    """
    history = chat_history or []
    llm = get_text_llm()  # Fix #3: singleton, not a new instance per request

    setup_and_retrieval = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
        "chat_history": RunnableLambda(lambda _: history),
    }

    chain = (
        setup_and_retrieval
        | RunnableLambda(build_prompt)
        | llm
        | StrOutputParser()
    )

    # Fix #1: carries context through so the caller gets sources that exactly
    # match what the LLM received — eliminates the second retrieval call
    chain_with_sources = setup_and_retrieval | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | llm
            | StrOutputParser()
        )
    )

    return chain, chain_with_sources
