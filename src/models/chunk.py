"""Chunk database model."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.document import Document


class ChunkType(str, Enum):
    """Chunk content type."""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    HEADING = "heading"


class Chunk(Base, UUIDMixin, TimestampMixin):
    """Database model for document chunk metadata."""
    __tablename__ = "chunks"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    chunk_type: Mapped[ChunkType] = mapped_column(
        SQLEnum(ChunkType), default=ChunkType.TEXT, nullable=False,
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vector_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<Chunk(id='{self.id}', doc='{self.document_id}', type='{self.chunk_type.value}', page={self.page_number})>"

    @property
    def effective_vector_id(self) -> str:
        return self.vector_id or self.id
