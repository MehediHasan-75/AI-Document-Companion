"""Conversation and message persistence service."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.core.exceptions import DocumentNotFoundError
from src.models.conversation import Conversation
from src.models.message import Message, MessageRole

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES: int = 20


class ConversationService:
    """Manages conversation lifecycle and message history."""

    def create_conversation(self, db: Session, title: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info("Created conversation %s", conversation.id)
        return conversation

    def get_conversation(self, db: Session, conversation_id: str) -> Conversation:
        """Get a conversation by ID or raise."""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.is_active.is_(True),
        ).first()
        if not conversation:
            raise DocumentNotFoundError(f"Conversation '{conversation_id}' not found")
        return conversation

    def list_conversations(self, db: Session) -> List[Dict[str, Any]]:
        """List all active conversations."""
        conversations = (
            db.query(Conversation)
            .filter(Conversation.is_active.is_(True))
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        return [
            {
                "id": c.id,
                "title": c.title,
                "message_count": c.message_count,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in conversations
        ]

    def delete_conversation(self, db: Session, conversation_id: str) -> None:
        """Soft-delete a conversation."""
        conversation = self.get_conversation(db, conversation_id)
        conversation.deactivate()
        db.commit()
        logger.info("Deactivated conversation %s", conversation_id)

    def add_message(
        self,
        db: Session,
        conversation_id: str,
        role: MessageRole,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """Append a message to a conversation."""
        conversation = self.get_conversation(db, conversation_id)

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources or [],
        )
        db.add(message)

        conversation.update_last_message()
        if conversation.message_count == 1:
            conversation.set_title_from_first_message(content)

        db.commit()
        db.refresh(message)
        return message

    def get_history(
        self,
        db: Session,
        conversation_id: str,
        limit: int = MAX_HISTORY_MESSAGES,
    ) -> List[Dict[str, str]]:
        """Return recent messages as role/content dicts for LLM context."""
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )
        # Reverse to chronological order
        messages.reverse()
        return [{"role": m.role.value, "content": m.content} for m in messages]

    def get_messages(self, db: Session, conversation_id: str) -> List[Dict[str, Any]]:
        """Return all messages for a conversation (API response format)."""
        self.get_conversation(db, conversation_id)  # validate exists
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return [
            {
                "id": m.id,
                "role": m.role.value,
                "content": m.content,
                "sources": m.sources,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]


conversation_service = ConversationService()
