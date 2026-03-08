"""
Conversation Database Model.

Defines the Conversation model for managing chat sessions in the RAG system.
Conversations group related messages and maintain context for multi-turn
dialogue.

Architecture:
    - UUID primary key for distributed compatibility
    - Optional user association for authenticated sessions
    - Metadata storage for conversation settings
    - Soft delete for audit trails

Integration Points:
    - REDIS_INTEGRATION: Cache active conversations
    - WEBSOCKET_INTEGRATION: Real-time conversation updates

Example:
    >>> from src.models.conversation import Conversation
    >>> conv = Conversation(title="Research Discussion")
    >>> session.add(conv)
    >>> session.commit()
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.message import Message


# =============================================================================
# Conversation Model
# =============================================================================

class Conversation(Base, UUIDMixin, TimestampMixin):
    """
    Database model for chat conversations.
    
    Represents a conversation session containing multiple messages.
    Supports optional user association and conversation metadata.
    
    Attributes:
        id: UUID primary key.
        title: Display title for the conversation.
        user_id: Optional user identifier (for authenticated sessions).
        document_ids: JSON array of document IDs in conversation context.
        is_active: Whether conversation is currently active.
        last_message_at: Timestamp of most recent message.
        message_count: Number of messages in conversation.
        metadata: JSON object for additional settings.
        messages: Relationship to Message records.
    
    Integration Points:
        - REDIS_INTEGRATION: Cache conversation state
        - WEBSOCKET_INTEGRATION: Push updates to clients
    
    Example:
        >>> conv = Conversation(title="AI Discussion")
        >>> conv.add_message("user", "What is machine learning?")
    """
    __tablename__ = "conversations"
    
    # Conversation Information
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Display title"
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="User identifier for authenticated sessions"
    )
    
    # Context
    document_ids: Mapped[Optional[List]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="Document IDs included in conversation context"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether conversation is active"
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of last message"
    )
    message_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Number of messages"
    )
    
    # Additional Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional conversation settings"
    )
    
    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id='{self.id}', title='{self.title}', messages={self.message_count})>"
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def update_last_message(self) -> None:
        """
        Update last_message_at timestamp and increment message count.
        
        Call this after adding a new message to the conversation.
        """
        self.last_message_at = datetime.utcnow()
        self.message_count += 1
    
    def add_document_context(self, document_id: str) -> None:
        """
        Add a document to the conversation context.
        
        Args:
            document_id: ID of document to add to context.
        """
        if self.document_ids is None:
            self.document_ids = []
        if document_id not in self.document_ids:
            self.document_ids.append(document_id)
    
    def deactivate(self) -> None:
        """Mark conversation as inactive."""
        self.is_active = False
    
    def set_title_from_first_message(self, message: str, max_length: int = 50) -> None:
        """
        Auto-generate title from first message content.
        
        Args:
            message: First message content.
            max_length: Maximum title length.
        """
        if not self.title:
            truncated = message[:max_length]
            if len(message) > max_length:
                truncated += "..."
            self.title = truncated
