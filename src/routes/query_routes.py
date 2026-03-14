"""
Query routes for RAG question answering.
"""

from fastapi import APIRouter, Depends

from src.controllers.query_controller import query_controller
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.query import QueryRequest

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/ask", summary="Ask a question over ingested documents")
async def ask(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Ask a question over the currently ingested documents.
    """
    return query_controller.ask_with_sources(payload.question)
