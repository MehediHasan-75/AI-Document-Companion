"""
Document Database Model.

Defines the Document model for storing document metadata in the database.
Actual document content is stored in the docstore (JSON/Redis), while
metadata and status are stored here.

Architecture:
    - UUID primary key for distributed compatibility
    - Tracks processing status and metadata
    - Relationships to chunks for granular access
    - Soft delete support for audit trails

Integration Points:
    - REDIS_INTEGRATION: Cache document metadata
    - S3_INTEGRATION: Store file_path as S3 keys

Example:
    >>> from src.models.document import Document
    >>> doc = Document(
    ...     filename="report.pdf",
    ...     content_type="application/pdf"
    ... )
    >>> session.add(doc)
    >>> session.commit()
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.chunk import Chunk


# =============================================================================
# Enumerations
# =============================================================================

class DocumentStatus(str, Enum):
    """
    Document processing status enumeration.
    
    Tracks the lifecycle of a document through the ingestion pipeline.
    
    Attributes:
        UPLOADED: File uploaded, not yet processed.
        PROCESSING: Currently being processed by RAG pipeline.
        PROCESSED: Successfully processed and indexed.
        FAILED: Processing failed with error.
        DELETED: Soft-deleted document.
    """
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentType(str, Enum):
    """
    Document content type enumeration.
    
    Attributes:
        PDF: PDF document.
        DOCX: Microsoft Word document.
        TXT: Plain text file.
        MD: Markdown file.
        HTML: HTML document.
        OTHER: Other file types.
    """
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    OTHER = "other"


# =============================================================================
# Document Model
# =============================================================================

class Document(Base, UUIDMixin, TimestampMixin):
    """
    Database model for document metadata.
    
    Stores metadata about uploaded documents including filename, type,
    processing status, and statistics. The actual document content is
    stored separately in the docstore.
    
    Attributes:
        id: UUID primary key.
        filename: Original filename of the uploaded document.
        content_type: MIME type of the document.
        doc_type: Categorized document type.
        file_path: Path to the stored file (local or S3 key).
        file_size: Size of the file in bytes.
        page_count: Number of pages (for PDFs).
        chunk_count: Number of chunks created during processing.
        status: Current processing status.
        error_message: Error details if processing failed.
        processed_at: Timestamp when processing completed.
        chunks: Relationship to associated Chunk records.
    
    Integration Points:
        - S3_INTEGRATION: file_path becomes S3 object key
        - REDIS_INTEGRATION: Cache frequently accessed metadata
    
    Example:
        >>> doc = Document(
        ...     filename="research.pdf",
        ...     content_type="application/pdf",
        ...     file_size=1024000
        ... )
    """
    __tablename__ = "documents"
    
    # File Information
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Original filename"
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME type"
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType),
        default=DocumentType.OTHER,
        nullable=False,
        comment="Categorized document type"
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Storage path or S3 key"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="File size in bytes"
    )
    
    # Processing Information
    page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of pages"
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of chunks created"
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.UPLOADED,
        nullable=False,
        index=True,
        comment="Processing status"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if processing failed"
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When processing completed"
    )
    
    # Relationships
    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<Document(id='{self.id}', filename='{self.filename}', status='{self.status.value}')>"
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def mark_processing(self) -> None:
        """Mark document as currently processing."""
        self.status = DocumentStatus.PROCESSING
        self.error_message = None
    
    def mark_processed(self, chunk_count: int = 0, page_count: int | None = None) -> None:
        """
        Mark document as successfully processed.
        
        Args:
            chunk_count: Number of chunks created.
            page_count: Number of pages in document.
        """
        self.status = DocumentStatus.PROCESSED
        self.chunk_count = chunk_count
        self.page_count = page_count
        self.processed_at = datetime.utcnow()
        self.error_message = None
    
    def mark_failed(self, error: str) -> None:
        """
        Mark document processing as failed.
        
        Args:
            error: Error message describing the failure.
        """
        self.status = DocumentStatus.FAILED
        self.error_message = error
    
    @classmethod
    def get_doc_type(cls, content_type: str) -> DocumentType:
        """
        Determine document type from MIME type.
        
        Args:
            content_type: MIME type string.
        
        Returns:
            Corresponding DocumentType enum value.
        """
        mime_mapping = {
            "application/pdf": DocumentType.PDF,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
            "text/plain": DocumentType.TXT,
            "text/markdown": DocumentType.MD,
            "text/html": DocumentType.HTML,
        }
        return mime_mapping.get(content_type, DocumentType.OTHER)
