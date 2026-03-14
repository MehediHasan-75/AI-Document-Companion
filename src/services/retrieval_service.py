"""Multi-vector retrieval service for the RAG pipeline."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from src.config.constants import DEFAULT_SEARCH_K, DEFAULT_SEARCH_TYPE, DEFAULT_ID_KEY
from src.services.vector_service import SimpleDocStore

logger = logging.getLogger(__name__)


class SourceResult(TypedDict):
    summary: str
    original: Optional[str]
    type: str
    doc_id: Optional[str]


def get_multi_vector_retriever(
    vectorstore: Chroma,
    search_type: str = DEFAULT_SEARCH_TYPE,
    search_k: int = DEFAULT_SEARCH_K,
) -> Tuple[VectorStoreRetriever, str]:
    """Create a retriever from a vectorstore. Returns (retriever, id_key)."""
    id_key = DEFAULT_ID_KEY
    retriever = vectorstore.as_retriever(
        search_type=search_type,
        search_kwargs={"k": search_k},
    )
    return retriever, id_key


def add_documents_to_retriever(
    vectorstore: Chroma,
    docstore: SimpleDocStore,
    texts: Optional[List[Any]] = None,
    text_summaries: Optional[List[str]] = None,
    tables: Optional[List[Any]] = None,
    table_summaries: Optional[List[str]] = None,
    images: Optional[List[str]] = None,
    image_summaries: Optional[List[str]] = None,
    id_key: str = DEFAULT_ID_KEY,
) -> Dict[str, int]:
    """Index documents: summaries in vector store, originals in doc store."""
    counts = {"texts": 0, "tables": 0, "images": 0}

    if texts and text_summaries:
        if len(texts) != len(text_summaries):
            raise ValueError(
                f"Texts and summaries length mismatch: {len(texts)} vs {len(text_summaries)}"
            )
        text_ids = [str(uuid.uuid4()) for _ in texts]
        summary_docs = [
            Document(
                page_content=summary,
                metadata={id_key: text_ids[i], "type": "text"},
            )
            for i, summary in enumerate(text_summaries)
        ]
        vectorstore.add_documents(summary_docs)
        docstore.mset(list(zip(text_ids, [str(t) for t in texts])))
        counts["texts"] = len(texts)
        logger.info("Added %d text chunks", len(texts))

    if tables and table_summaries:
        if len(tables) != len(table_summaries):
            raise ValueError(
                f"Tables and summaries length mismatch: {len(tables)} vs {len(table_summaries)}"
            )
        table_ids = [str(uuid.uuid4()) for _ in tables]
        summary_docs = [
            Document(
                page_content=summary,
                metadata={id_key: table_ids[i], "type": "table"},
            )
            for i, summary in enumerate(table_summaries)
        ]
        vectorstore.add_documents(summary_docs)
        table_contents = [
            t.metadata.text_as_html if hasattr(t, "metadata") else str(t) for t in tables
        ]
        docstore.mset(list(zip(table_ids, table_contents)))
        counts["tables"] = len(tables)
        logger.info("Added %d tables", len(tables))

    if images and image_summaries:
        if len(images) != len(image_summaries):
            raise ValueError(
                f"Images and summaries length mismatch: {len(images)} vs {len(image_summaries)}"
            )
        img_ids = [str(uuid.uuid4()) for _ in images]
        summary_docs = [
            Document(
                page_content=summary,
                metadata={id_key: img_ids[i], "type": "image"},
            )
            for i, summary in enumerate(image_summaries)
        ]
        vectorstore.add_documents(summary_docs)
        docstore.mset(list(zip(img_ids, images)))
        counts["images"] = len(images)
        logger.info("Added %d images", len(images))

    return counts


def retrieve_with_sources(
    retriever: VectorStoreRetriever,
    docstore: SimpleDocStore,
    query: str,
    id_key: str = DEFAULT_ID_KEY,
) -> List[SourceResult]:
    """Retrieve matching summaries and their original source content."""
    matched_summaries = retriever.invoke(query)

    results: List[SourceResult] = []
    for doc in matched_summaries:
        doc_id = doc.metadata.get(id_key)
        original = docstore.get(doc_id) if doc_id else None
        results.append(
            {
                "summary": doc.page_content,
                "original": original,
                "type": doc.metadata.get("type", "text"),
                "doc_id": doc_id,
            }
        )

    logger.info("Retrieved %d sources for query", len(results))
    return results
