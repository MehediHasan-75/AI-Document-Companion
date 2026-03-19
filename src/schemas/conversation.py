"""Pydantic schemas for conversation endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.config.constants import MAX_QUESTION_LENGTH


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: str


class DeleteConversationResponse(BaseModel):
    message: str
    id: str
