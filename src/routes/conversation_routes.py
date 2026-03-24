"""Conversation routes for chat with memory."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
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
from src.services.streaming_service import stream_chat_response

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
    summary="Ask a question — streams response token-by-token via SSE",
    responses={
        401: {"description": "Invalid or expired token"},
        404: {"description": "Conversation not found"},
        422: {"description": "Query failed"},
    },
)
async def ask_in_conversation(
    conversation_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ask a question with full conversation history as context.

    Streams the LLM response token-by-token via Server-Sent Events.
    Previous messages are automatically loaded and injected into the
    LLM prompt for context-aware follow-up answers.

    **SSE event types:**

    - ``{"type": "delta", "content": "..."}`` — incremental token
    - ``{"type": "complete", "content": "...", "conversation_id": "...", "sources": [...]}`` — final
    - ``{"type": "error", "content": "..."}`` — error
    """
    return StreamingResponse(
        stream_chat_response(
            question=payload.question,
            user_id=current_user.id,
            db=db,
            conversation_id=conversation_id,
            doc_ids=payload.doc_ids,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
