"""
Chunk Database Model.

Defines the Chunk model for storing document chunk metadata in the database.
Actual chunk content and embeddings are stored in the vector store, while
metadata is stored here for querying and management.

Architecture:
    - UUID primary key matching vector store IDs
    - Foreign key to parent Document
    - Stores chunk metadata (page, position, type)
    - Links to vector store entries

Integration Points:
    - CHROMA_INTEGRATION: Sync with vector store IDs
    - REDIS_INTEGRATION: Cache chunk metadata

Example:
    >>> from src.models.chunk import Chunk, ChunkType
    >>> chunk = Chunk(
    ...     document_id=doc.id,
    ...     chunk_type=ChunkType.TEXT,
    ...     page_number=1
    ... )
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.document import Document


# =============================================================================
# Enumerations
# =============================================================================

class ChunkType(str, Enum):
    """
    Chunk content type enumeration.
    
    Attributes:
        TEXT: Text content chunk.
        TABLE: Table/tabular data chunk.
        IMAGE: Image chunk (base64 stored in docstore).
        CODE: Code block chunk.
        HEADING: Section heading chunk.
    """
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    HEADING = "heading"


# =============================================================================
# Chunk Model
# =============================================================================

class Chunk(Base, UUIDMixin, TimestampMixin):
    """
    Database model for document chunk metadata.
    
    Stores metadata about document chunks that have been extracted
    and indexed. The actual content is stored in the docstore,
    and embeddings are stored in the vector store.
    
    Attributes:
        id: UUID primary key (matches vector store ID).
        document_id: Foreign key to parent Document.
        chunk_type: Type of content in chunk.
        page_number: Page number in original document.
        position: Position/order within the document.
        char_count: Number of characters in chunk.
        summary: LLM-generated summary (stored as embedding source).
        vector_id: ID in the vector store (if different from id).
        document: Relationship to parent Document.
    
    Integration Points:
        - CHROMA_INTEGRATION: vector_id links to Chroma
        - REDIS_INTEGRATION: Cache frequently accessed chunks
    
    Example:
        >>> chunk = Chunk(
        ...     document_id="doc-123",
        ...     chunk_type=ChunkType.TEXT,
        ...     page_number=1,
        ...     position=0
        ... )
    """
    __tablename__ = "chunks"
    
    # Document Reference
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent document ID"
    )
    
    # Chunk Information
    chunk_type: Mapped[ChunkType] = mapped_column(
        SQLEnum(ChunkType),
        default=ChunkType.TEXT,
        nullable=False,
        comment="Type of content"
    )
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Page number in document"
    )
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Order within document"
    )
    char_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Character count"
    )
    
    # Summary (used for embedding)
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="LLM-generated summary"
    )
    
    # Vector Store Reference
    vector_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="ID in vector store (if different from id)"
    )
    
    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks"
    )
    
    def __repr__(self) -> str:
        return f"<Chunk(id='{self.id}', doc='{self.document_id}', type='{self.chunk_type.value}', page={self.page_number})>"
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    @property
    def effective_vector_id(self) -> str:
        """
        Get the ID used in the vector store.
        
        Returns vector_id if set, otherwise returns the chunk id.
        """
        return self.vector_id or self.id
