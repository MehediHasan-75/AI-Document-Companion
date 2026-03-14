"""Vector store service for document embeddings and storage."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, List, Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import settings
from src.config.constants import DEFAULT_CHROMA_PERSIST_DIR, DEFAULT_DOCSTORE_PATH, COLLECTION_NAME

logger = logging.getLogger(__name__)

_vectorstore: Optional[Chroma] = None
_docstore: Optional["SimpleDocStore"] = None


class SimpleDocStore:
    """SQLite-backed key-value store for original document content.

    Fix #2: replaces the JSON implementation which rewrote the entire file on
    every write (O(n) cost) and had no protection against concurrent access.
    SQLite WAL mode allows multiple concurrent readers and atomic writes.
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        path = persist_path or ":memory:"
        # Transparently redirect legacy .json path to .db
        if path.endswith(".json"):
            path = path[:-5] + ".db"
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # Single persistent connection — required for :memory: and efficient for files
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS docstore "
            "(id TEXT PRIMARY KEY, content TEXT NOT NULL)"
        )
        self._conn.commit()

    def mset(self, items: List[tuple]) -> None:
        """Upsert multiple (id, content) pairs atomically."""
        rows = [
            (doc_id, content if isinstance(content, str) else str(content))
            for doc_id, content in items
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO docstore (id, content) VALUES (?, ?)", rows
        )
        self._conn.commit()

    def get(self, doc_id: str) -> Optional[Any]:
        row = self._conn.execute(
            "SELECT content FROM docstore WHERE id = ?", (doc_id,)
        ).fetchone()
        return row[0] if row else None

    def mget(self, doc_ids: List[str]) -> List[Optional[Any]]:
        return [self.get(doc_id) for doc_id in doc_ids]


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
