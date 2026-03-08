"""
Facade for LLM-based summarization and RAG chains.

Delegates to ``src.services.llm_service``.
"""

from src.services.llm_service import (
    get_text_table_summarizer,
    get_image_summarizer,
    parse_docs,
    build_prompt,
    get_rag_chain,
)

__all__ = [
    "get_text_table_summarizer",
    "get_image_summarizer",
    "parse_docs",
    "build_prompt",
    "get_rag_chain",
]

