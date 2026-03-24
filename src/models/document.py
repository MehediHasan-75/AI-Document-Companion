"""Document database model."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.chunk import Chunk


class DocumentStatus(str, Enum):
    """Document processing lifecycle status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentType(str, Enum):
    """Document content type."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    OTHER = "other"


class Document(Base, UUIDMixin, TimestampMixin):
    """Database model for document metadata."""
    __tablename__ = "documents"

    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    doc_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType), default=DocumentType.OTHER, nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    table_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False, index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan", lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Document(id='{self.id}', filename='{self.filename}', status='{self.status.value}')>"

    def mark_processing(self) -> None:
        self.status = DocumentStatus.PROCESSING
        self.error_message = None

    def mark_processed(
        self,
        chunk_count: int = 0,
        page_count: int | None = None,
        image_count: int | None = None,
        table_count: int | None = None,
    ) -> None:
        self.status = DocumentStatus.PROCESSED
        self.chunk_count = chunk_count
        self.page_count = page_count
        self.image_count = image_count
        self.table_count = table_count
        self.processed_at = datetime.utcnow()
        self.error_message = None

    def mark_failed(self, error: str) -> None:
        self.status = DocumentStatus.FAILED
        self.error_message = error

    @classmethod
    def get_doc_type(cls, content_type: str) -> DocumentType:
        mime_mapping = {
            "application/pdf": DocumentType.PDF,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
            "text/plain": DocumentType.TXT,
            "text/markdown": DocumentType.MD,
            "text/html": DocumentType.HTML,
        }
        return mime_mapping.get(content_type, DocumentType.OTHER)
