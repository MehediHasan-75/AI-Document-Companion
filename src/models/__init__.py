"""
Database Models Package.

This package contains SQLAlchemy ORM models for the RAG system.
Models are designed for use with PostgreSQL in production and
SQLite for development.

Exports:
    - Document: Document metadata model
    - DocumentStatus: Document processing status enum
    - DocumentType: Document type enum
    - Conversation: Chat conversation model
    - Message: Chat message model
    - MessageRole: Message sender role enum
    - Chunk: Document chunk metadata model
    - ChunkType: Chunk type enum
"""

from src.models.document import Document, DocumentStatus, DocumentType
from src.models.conversation import Conversation
from src.models.message import Message, MessageRole
from src.models.chunk import Chunk, ChunkType

__all__ = [
    # Document
    "Document",
    "DocumentStatus",
    "DocumentType",
    # Conversation
    "Conversation",
    # Message
    "Message",
    "MessageRole",
    # Chunk
    "Chunk",
    "ChunkType",
]
