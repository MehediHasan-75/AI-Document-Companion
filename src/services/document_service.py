"""Document service for database operations on documents."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)


class DocumentService:
    """Handles database queries for document metadata."""

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

        return {
            "files": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.status.value,
                    "created_at": doc.created_at.isoformat(),
                    "type": doc.doc_type.value,
                }
                for doc in documents
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }


document_service: DocumentService = DocumentService()
