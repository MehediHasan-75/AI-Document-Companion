"""
Query routes for RAG question answering.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from src.controllers.query_controller import query_controller


router = APIRouter(prefix="/query", tags=["Query"])


class QueryRequest(BaseModel):
    question: str


@router.post("/ask", summary="Ask a question over ingested documents")
async def ask(payload: QueryRequest):
    """
    Ask a question over the currently ingested documents.
    """
    return query_controller.ask(payload.question)
