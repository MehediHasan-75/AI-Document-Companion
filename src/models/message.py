"""
Message Database Model.

Defines the Message model for storing chat messages within conversations.
Supports both user messages and assistant responses with metadata.

Architecture:
    - UUID primary key for distributed compatibility
    - Foreign key to Conversation
    - Supports message roles (user, assistant, system)
    - Token counting for usage tracking

Integration Points:
    - REDIS_INTEGRATION: Cache recent messages
    - WEBSOCKET_INTEGRATION: Real-time message delivery

Example:
    >>> from src.models.message import Message, MessageRole
    >>> msg = Message(
    ...     conversation_id=conv.id,
    ...     role=MessageRole.USER,
    ...     content="What is AI?"
    ... )
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.conversation import Conversation


# =============================================================================
# Enumerations
# =============================================================================

class MessageRole(str, Enum):
    """
    Message sender role enumeration.
    
    Attributes:
        USER: Message from the user.
        ASSISTANT: Response from the AI assistant.
        SYSTEM: System message (instructions, context).
    """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# =============================================================================
# Message Model
# =============================================================================

class Message(Base, UUIDMixin, TimestampMixin):
    """
    Database model for chat messages.
    
    Stores individual messages within a conversation, including
    the message content, sender role, and associated metadata
    like token counts and source references.
    
    Attributes:
        id: UUID primary key.
        conversation_id: Foreign key to parent Conversation.
        role: Message sender role (user, assistant, system).
        content: Message text content.
        token_count: Number of tokens in message (for billing/limits).
        sources: JSON array of source references used in response.
        metadata: Additional message metadata.
        conversation: Relationship to parent Conversation.
    
    Integration Points:
        - REDIS_INTEGRATION: Cache recent messages per conversation
        - WEBSOCKET_INTEGRATION: Stream messages in real-time
    
    Example:
        >>> msg = Message(
        ...     conversation_id="conv-123",
        ...     role=MessageRole.USER,
        ...     content="Explain transformers"
        ... )
    """
    __tablename__ = "messages"
    
    # Conversation Reference
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent conversation ID"
    )
    
    # Message Content
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole),
        nullable=False,
        comment="Message sender role"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Message text content"
    )
    
    # Usage Tracking
    token_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Token count for billing"
    )
    
    # RAG Metadata
    sources: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="Source document references"
    )
    
    # Additional Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional message metadata"
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id='{self.id}', role='{self.role.value}', content='{content_preview}')>"
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def add_source(self, source_id: str, source_type: str = "document") -> None:
        """
        Add a source reference to the message.
        
        Args:
            source_id: ID of the source document/chunk.
            source_type: Type of source ("document", "chunk", "web").
        """
        if self.sources is None:
            self.sources = []
        self.sources.append({
            "id": source_id,
            "type": source_type
        })
    
    @property
    def is_user(self) -> bool:
        """Check if message is from user."""
        return self.role == MessageRole.USER
    
    @property
    def is_assistant(self) -> bool:
        """Check if message is from assistant."""
        return self.role == MessageRole.ASSISTANT
