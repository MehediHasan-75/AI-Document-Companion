"""LLM service for document summarization and question answering."""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src.config import settings
from src.config.constants import (
    LLM_MAX_RETRIES,
    QA_TEMPERATURE,
    SUMMARIZATION_TEMPERATURE,
    VISION_MODEL,
    VISION_TEMPERATURE,
)
from src.config.prompts import (
    IMAGE_SUMMARIZATION_PROMPT,
    SUMMARIZATION_SYSTEM_PROMPT,
    TEXT_TABLE_SUMMARIZATION_PROMPT,
)

logger = logging.getLogger(__name__)

_text_llm: Optional[ChatOllama] = None
_qa_llm: Optional[ChatOllama] = None
_vision_llm: Optional[ChatOllama] = None


def get_text_llm() -> ChatOllama:
    """Singleton LLM for summarization (low temperature for factual extraction)."""
    global _text_llm
    if _text_llm is None:
        _text_llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_HOST,
            temperature=SUMMARIZATION_TEMPERATURE,
        )
    return _text_llm


def get_qa_llm() -> ChatOllama:
    """Singleton LLM for QA (Ollama)."""
    global _qa_llm
    if _qa_llm is None:
        _qa_llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_HOST,
            temperature=QA_TEMPERATURE,
            reasoning=True,
        ).with_retry(stop_after_attempt=LLM_MAX_RETRIES)
    return _qa_llm


def _get_vision_llm() -> ChatOllama:
    global _vision_llm
    if _vision_llm is None:
        _vision_llm = ChatOllama(
            model=VISION_MODEL,
            base_url=settings.OLLAMA_HOST,
            temperature=VISION_TEMPERATURE,
            processor="cpu",
        )
    return _vision_llm


def get_text_table_summarizer() -> Any:
    """Create a chain for summarizing text and tables."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUMMARIZATION_SYSTEM_PROMPT),
        ("human", TEXT_TABLE_SUMMARIZATION_PROMPT),
    ])
    return {"element": lambda x: x} | prompt | get_text_llm() | StrOutputParser()


def get_image_summarizer() -> Any:
    """Create a chain for summarizing images using Llava."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUMMARIZATION_SYSTEM_PROMPT),
        (
            "human",
            [
                {"type": "text", "text": IMAGE_SUMMARIZATION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,{image}"},
                },
            ],
        ),
    ])
    return prompt | _get_vision_llm() | StrOutputParser()
