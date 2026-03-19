"""Conversation routes for chat with memory."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.dependencies.auth import get_current_user
from src.dependencies.db import get_db
from src.models.user import User
from src.schemas.conversation import (
    ChatRequest,
    ConversationResponse,
    CreateConversationRequest,
    DeleteConversationResponse,
)
from src.services.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=201,
    summary="Create a new conversation",
    responses={401: {"description": "Invalid or expired token"}},
)
def create_conversation(
    payload: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = conversation_service.create_conversation(db, user_id=current_user.id, title=payload.title)
    return {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()}


@router.get(
    "",
    summary="List all conversations",
    responses={401: {"description": "Invalid or expired token"}},
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return conversation_service.list_conversations(db, user_id=current_user.id)


@router.get(
    "/{conversation_id}/messages",
    summary="Get conversation messages",
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Conversation not found"},
    },
)
def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return conversation_service.get_messages(db, conversation_id, user_id=current_user.id)


@router.post(
    "/{conversation_id}/ask",
    summary="Ask a question within a conversation",
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Conversation not found"},
        422: {"description": "Query failed"},
    },
)
def ask_in_conversation(
    conversation_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ask a question with full conversation history as context.

    Previous messages are automatically loaded and injected into the
    LLM prompt so the model can give context-aware follow-up answers.
    """
    return conversation_service.ask(db, conversation_id, payload.question, user_id=current_user.id)


@router.delete(
    "/{conversation_id}",
    response_model=DeleteConversationResponse,
    summary="Delete a conversation",
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Conversation not found"},
    },
)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation_service.delete_conversation(db, conversation_id, user_id=current_user.id)
    return {"message": "Conversation deleted", "id": conversation_id}
