"""Vector store service for document embeddings and storage."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import settings
from src.config.constants import DEFAULT_CHROMA_PERSIST_DIR, DEFAULT_DOCSTORE_PATH, COLLECTION_NAME

logger = logging.getLogger(__name__)

_vectorstore: Optional[Chroma] = None
_docstore: Optional["SimpleDocStore"] = None


class SimpleDocStore:
    """JSON-persisted key-value store for original document content."""

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self.store: Dict[str, Any] = {}
        self.persist_path: Optional[str] = persist_path

        if persist_path and os.path.exists(persist_path):
            self._load()

    def mset(self, items: List[tuple]) -> None:
        """Set multiple documents at once."""
        for doc_id, content in items:
            if hasattr(content, "text"):
                self.store[doc_id] = str(content)
            else:
                self.store[doc_id] = content
        self._save()

    def get(self, doc_id: str) -> Optional[Any]:
        """Get a single document by ID."""
        return self.store.get(doc_id)

    def mget(self, doc_ids: List[str]) -> List[Optional[Any]]:
        """Get multiple documents by IDs."""
        return [self.store.get(doc_id) for doc_id in doc_ids]

    def _save(self) -> None:
        if self.persist_path:
            Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.store, f, ensure_ascii=False, indent=2)

    def _load(self) -> None:
        if self.persist_path and os.path.exists(self.persist_path):
            with open(self.persist_path, "r", encoding="utf-8") as f:
                self.store = json.load(f)


def get_vectorstore(persist_directory: str = DEFAULT_CHROMA_PERSIST_DIR) -> Chroma:
    """Return a singleton Chroma vector store for document summaries."""
    global _vectorstore

    if _vectorstore is None:
        logger.info("Initializing Chroma vector store at %s", persist_directory)
        embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model_name)
        _vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )

    return _vectorstore


def get_docstore(persist_path: str = DEFAULT_DOCSTORE_PATH) -> SimpleDocStore:
    """Return a singleton SimpleDocStore for original content."""
    global _docstore

    if _docstore is None:
        logger.info("Initializing document store at %s", persist_path)
        _docstore = SimpleDocStore(persist_path=persist_path)

    return _docstore
