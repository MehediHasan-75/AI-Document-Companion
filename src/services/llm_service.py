"""LLM service for document summarization."""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src.config import settings
from src.config.constants import SUMMARIZATION_TEMPERATURE, VISION_MODEL, VISION_TEMPERATURE
from src.config.prompts import TEXT_TABLE_SUMMARIZATION_PROMPT, IMAGE_SUMMARIZATION_PROMPT

logger = logging.getLogger(__name__)

# Fix #3: singleton LLM instances — one connection reused across all requests
_text_llm: Optional[ChatOllama] = None
_vision_llm: Optional[ChatOllama] = None


def get_text_llm() -> ChatOllama:
    global _text_llm
    if _text_llm is None:
        _text_llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_HOST,
            temperature=SUMMARIZATION_TEMPERATURE,
        )
    return _text_llm


def _get_vision_llm() -> ChatOllama:
    global _vision_llm
    if _vision_llm is None:
        _vision_llm = ChatOllama(
            model=VISION_MODEL,
            base_url=settings.OLLAMA_HOST,
            temperature=VISION_TEMPERATURE,
        )
    return _vision_llm


def get_text_table_summarizer() -> Any:
    """Create a chain for summarizing text and tables."""
    prompt = ChatPromptTemplate.from_template(TEXT_TABLE_SUMMARIZATION_PROMPT)
    return {"element": lambda x: x} | prompt | get_text_llm() | StrOutputParser()


def get_image_summarizer() -> Any:
    """Create a chain for summarizing images using Llava."""
    messages = [
        (
            "user",
            [
                {"type": "text", "text": IMAGE_SUMMARIZATION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,{image}"},
                },
            ],
        )
    ]
    prompt = ChatPromptTemplate.from_messages(messages)
    return prompt | _get_vision_llm() | StrOutputParser()
