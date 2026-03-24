"""Document ingestion service for the RAG pipeline."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.vectorstores import VectorStoreRetriever

from src.config.constants import DEFAULT_MAX_CONCURRENCY
from src.services.unstructured_service import partition_document
from src.services.chunk_service import separate_elements, extract_images_base64
from src.services.llm_service import get_text_table_summarizer, get_image_summarizer
from src.services.vector_service import get_vectorstore, get_docstore, SimpleDocStore
from src.services.retrieval_service import (
    get_multi_vector_retriever,
    add_documents_to_retriever,
)

logger = logging.getLogger(__name__)


class IngestionResult(TypedDict):
    retriever: VectorStoreRetriever
    docstore: SimpleDocStore
    chunk_count: int
    image_count: int
    table_count: int


def ingest_document_pipeline(
    file_path: str,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    user_id: Optional[str] = None,
) -> IngestionResult:
    """
    Run the full ingestion pipeline for a document:
    1. Partition into text, tables, images
    2. Summarize each content type via LLM
    3. Store summaries in vector DB, originals in doc store

    When user_id is provided, documents are tagged with it in metadata
    so retrieval can be scoped per-user.
    """
    logger.info("Starting ingestion pipeline for %s", file_path)

    chunks = partition_document(file_path)

    texts, tables = separate_elements(chunks)
    images = extract_images_base64(chunks)
    logger.info(
        "Extracted: %d texts, %d tables, %d images",
        len(texts),
        len(tables),
        len(images),
    )

    text_table_summarizer_chain = get_text_table_summarizer()

    text_summaries: List[str] = []
    if texts:
        text_summaries = text_table_summarizer_chain.batch(
            [str(t) for t in texts],
            {"max_concurrency": max_concurrency},
        )

    table_summaries: List[str] = []
    if tables:
        tables_html = [table.metadata.text_as_html for table in tables]
        table_summaries = text_table_summarizer_chain.batch(
            tables_html,
            {"max_concurrency": max_concurrency},
        )

    image_summaries: List[str] = []
    if images:
        image_summarizer_chain = get_image_summarizer()
        image_summaries = image_summarizer_chain.batch(
            images,
            {"max_concurrency": max_concurrency},
        )

    vectorstore = get_vectorstore()
    docstore = get_docstore()
    retriever, id_key = get_multi_vector_retriever(vectorstore, user_id=user_id)

    counts = add_documents_to_retriever(
        vectorstore,
        docstore,
        texts,
        text_summaries,
        tables,
        table_summaries,
        images,
        image_summaries,
        id_key,
        user_id=user_id,
    )

    total_chunks = counts["texts"] + counts["tables"] + counts["images"]
    logger.info("Ingestion pipeline completed for %s", file_path)

    return {
        "retriever": retriever,
        "docstore": docstore,
        "chunk_count": total_chunks,
        "image_count": counts["images"],
        "table_count": counts["tables"],
    }
