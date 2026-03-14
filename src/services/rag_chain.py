"""RAG chain construction for question answering."""

from __future__ import annotations

import logging
from base64 import b64decode
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_ollama import ChatOllama

from src.config import settings
from src.config.constants import SUMMARIZATION_TEMPERATURE

logger = logging.getLogger(__name__)


def _get_text_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_HOST,
        temperature=SUMMARIZATION_TEMPERATURE,
    )


def parse_docs(docs: List[Document]) -> Dict[str, List[Any]]:
    """Split retrieved documents into base64-encoded images and text documents."""
    b64_images: List[str] = []
    text_docs: List[Document] = []

    for doc in docs:
        try:
            b64decode(doc)
            b64_images.append(doc)
        except Exception:
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

    # Build history section
    history_section = ""
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role_label}: {msg['content']}")
        history_section = f"\nConversation history:\n" + "\n".join(history_lines) + "\n"

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

    When chat_history is provided, it is injected into the prompt so the LLM
    can produce context-aware follow-up answers.
    """
    history = chat_history or []

    setup_and_retrieval = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
        "chat_history": RunnableLambda(lambda _: history),
    }

    chain = (
        setup_and_retrieval
        | RunnableLambda(build_prompt)
        | _get_text_llm()
        | StrOutputParser()
    )

    chain_with_sources = setup_and_retrieval | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | _get_text_llm()
            | StrOutputParser()
        )
    )

    return chain, chain_with_sources
