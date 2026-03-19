"""Pydantic schemas for conversation endpoints."""

from typing import Optional

from pydantic import BaseModel, Field

from src.config.constants import MAX_QUESTION_LENGTH


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)
