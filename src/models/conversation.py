"""Conversation database model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.message import Message


class Conversation(Base, UUIDMixin, TimestampMixin):
    """Database model for chat conversations."""
    __tablename__ = "conversations"

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    document_ids: Mapped[Optional[List]] = mapped_column(JSON, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    message_count: Mapped[int] = mapped_column(default=0, nullable=False)
    conversation_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True, default=dict,
    )

    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id='{self.id}', title='{self.title}', messages={self.message_count})>"

    def update_last_message(self) -> None:
        self.last_message_at = datetime.utcnow()
        self.message_count += 1

    def add_document_context(self, document_id: str) -> None:
        if self.document_ids is None:
            self.document_ids = []
        if document_id not in self.document_ids:
            self.document_ids.append(document_id)

    def deactivate(self) -> None:
        self.is_active = False

    def set_title_from_first_message(self, message: str, max_length: int = 50) -> None:
        if not self.title:
            truncated = message[:max_length]
            if len(message) > max_length:
                truncated += "..."
            self.title = truncated
