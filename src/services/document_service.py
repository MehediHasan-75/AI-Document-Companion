"""Document service for database operations on documents."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.chunk import Chunk, ChunkType
from src.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)


class DocumentService:
    """Handles database queries for document metadata."""

    def create_document(
        self,
        db: Session,
        doc_id: str,
        filename: str,
        content_type: str,
        user_id: str,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
    ) -> Document:
        """Create a Document row after a successful file upload."""
        doc = Document(
            id=doc_id,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            doc_type=Document.get_doc_type(content_type),
            file_path=file_path,
            file_size=file_size,
            status=DocumentStatus.UPLOADED,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        logger.info("Document record created: %s for user %s", doc_id, user_id)
        return doc

    def list_documents(
        self,
        db: Session,
        user_id: str,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List all documents for the given user, sorted by created_at desc."""
        query = (
            db.query(Document)
            .filter(
                Document.user_id == user_id,
                Document.status != DocumentStatus.DELETED,
            )
            .order_by(Document.created_at.desc())
        )

        total = query.count()

        if page is not None and limit is not None:
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)
        else:
            page = 1
            limit = total

        documents = query.all()

        # Count image and table chunks per document in one query
        doc_ids = [doc.id for doc in documents]
        chunk_counts = (
            db.query(Chunk.document_id, Chunk.chunk_type, func.count().label("n"))
            .filter(
                Chunk.document_id.in_(doc_ids),
                Chunk.chunk_type.in_([ChunkType.IMAGE, ChunkType.TABLE]),
            )
            .group_by(Chunk.document_id, Chunk.chunk_type)
            .all()
        ) if doc_ids else []

        image_counts: Dict[str, int] = {}
        table_counts: Dict[str, int] = {}
        for doc_id, ctype, n in chunk_counts:
            if ctype == ChunkType.IMAGE:
                image_counts[doc_id] = n
            else:
                table_counts[doc_id] = n

        return {
            "files": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.status.value,
                    "created_at": doc.created_at.isoformat(),
                    "type": doc.doc_type.value,
                    "file_size": doc.file_size,
                    "page_count": doc.page_count,
                    "chunk_count": doc.chunk_count,
                    "image_count": image_counts.get(doc.id),
                    "table_count": table_counts.get(doc.id),
                }
                for doc in documents
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }


document_service: DocumentService = DocumentService()
