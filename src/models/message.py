"""Message database model."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.conversation import Conversation


class MessageRole(str, Enum):
    """Message sender role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base, UUIDMixin, TimestampMixin):
    """Database model for chat messages."""
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    message_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True, default=dict,
    )

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id='{self.id}', role='{self.role.value}', content='{content_preview}')>"

    def add_source(self, source_id: str, source_type: str = "document") -> None:
        if self.sources is None:
            self.sources = []
        self.sources.append({"id": source_id, "type": source_type})

    @property
    def is_user(self) -> bool:
        return self.role == MessageRole.USER

    @property
    def is_assistant(self) -> bool:
        return self.role == MessageRole.ASSISTANT
