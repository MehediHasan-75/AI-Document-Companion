"""Pydantic schemas for conversation endpoints."""

from typing import Optional

from pydantic import BaseModel


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class ChatRequest(BaseModel):
    question: str
