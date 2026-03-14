"""
Query routes for RAG question answering.
"""

from fastapi import APIRouter

from src.controllers.query_controller import query_controller
from src.schemas.query import QueryRequest

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/ask", summary="Ask a question over ingested documents")
async def ask(payload: QueryRequest):
    """
    Ask a question over the currently ingested documents.
    """
    return query_controller.ask_with_sources(payload.question)
