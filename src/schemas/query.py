"""Pydantic schemas for query endpoints."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.config.constants import MAX_QUESTION_LENGTH


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)
    chat_history: Optional[List[Dict[str, str]]] = None
