"""Pydantic schemas for query endpoints."""

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
