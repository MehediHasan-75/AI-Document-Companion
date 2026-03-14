"""Conversation routes for chat with memory."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.controllers.conversation_controller import conversation_controller
from src.dependencies.auth import get_current_user
from src.dependencies.db import get_db
from src.models.user import User
from src.schemas.conversation import ChatRequest, CreateConversationRequest

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", summary="Create a new conversation")
async def create_conversation(
    payload: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return conversation_controller.create_conversation(db, user_id=current_user.id, title=payload.title)


@router.get("", summary="List all conversations")
async def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return conversation_controller.list_conversations(db, user_id=current_user.id)


@router.get("/{conversation_id}/messages", summary="Get conversation messages")
async def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return conversation_controller.get_messages(db, conversation_id, user_id=current_user.id)


@router.post("/{conversation_id}/ask", summary="Ask a question within a conversation")
async def ask_in_conversation(
    conversation_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ask a question with full conversation history as context.

    Previous messages are automatically loaded and injected into the
    LLM prompt so the model can give context-aware follow-up answers.
    """
    return conversation_controller.ask(db, conversation_id, payload.question, user_id=current_user.id)


@router.delete("/{conversation_id}", summary="Delete a conversation")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return conversation_controller.delete_conversation(db, conversation_id, user_id=current_user.id)
