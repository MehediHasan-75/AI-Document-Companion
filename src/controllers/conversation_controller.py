"""Conversation controller for chat with memory."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.message import MessageRole
from src.services.conversation_service import conversation_service
from src.services.query_service import query_service

logger = logging.getLogger(__name__)


class ConversationController:
    """Controller for conversation lifecycle and chat-with-memory."""

    def create_conversation(
        self, db: Session, user_id: str, title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new conversation."""
        conv = conversation_service.create_conversation(db, user_id=user_id, title=title)
        return {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()}

    def list_conversations(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """List all active conversations for the current user."""
        return conversation_service.list_conversations(db, user_id=user_id)

    def get_messages(self, db: Session, conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a conversation."""
        return conversation_service.get_messages(db, conversation_id, user_id=user_id)

    def delete_conversation(self, db: Session, conversation_id: str, user_id: str) -> Dict[str, str]:
        """Soft-delete a conversation."""
        conversation_service.delete_conversation(db, conversation_id, user_id=user_id)
        return {"message": "Conversation deleted", "id": conversation_id}

    def ask(
        self, db: Session, conversation_id: str, question: str, user_id: str,
    ) -> Dict[str, Any]:
        """Ask a question within a conversation, preserving chat history.

        1. Load previous messages as chat history
        2. Save the user message
        3. Run RAG query with history injected
        4. Save the assistant message with sources
        5. Return the answer
        """
        # 1. Load history (before adding the new question)
        history = conversation_service.get_history(db, conversation_id, user_id=user_id)

        # 2. Persist user message
        conversation_service.add_message(
            db, conversation_id, MessageRole.USER, question, user_id=user_id,
        )

        # 3. RAG query with conversation context
        result = query_service.ask_with_sources(question, chat_history=history)

        # 4. Persist assistant response
        conversation_service.add_message(
            db,
            conversation_id,
            MessageRole.ASSISTANT,
            result["answer"],
            user_id=user_id,
            sources=result["sources"],
        )

        logger.info(
            "Conversation %s: answered with %d sources",
            conversation_id, len(result["sources"]),
        )

        return {
            "conversation_id": conversation_id,
            "answer": result["answer"],
            "sources": result["sources"],
        }


conversation_controller = ConversationController()
