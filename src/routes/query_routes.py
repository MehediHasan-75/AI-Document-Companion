"""
Query routes for RAG question answering.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.query import QueryRequest
from src.services.query_service import query_service
from src.services.rag_chain import get_rag_chain
from src.services.retrieval_service import get_multi_vector_retriever
from src.services.vector_service import get_vectorstore

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/ask", summary="Ask a question over ingested documents")
def ask(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Ask a question over the currently ingested documents.
    """
    return query_service.ask_with_sources(
        payload.question,
        chat_history=payload.chat_history,
        user_id=current_user.id,
    )


@router.post("/ask/stream", summary="Ask a question with streaming response")
async def ask_stream(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    """Stream the LLM response token-by-token via Server-Sent Events."""
    vectorstore = get_vectorstore()
    retriever, _ = get_multi_vector_retriever(vectorstore, user_id=current_user.id)
    chain = get_rag_chain(retriever, chat_history=payload.chat_history)

    async def event_generator():
        async for chunk in chain.astream(payload.question):
            # The chain emits partial dicts; we only stream the response tokens
            if isinstance(chunk, dict) and "response" in chunk:
                yield f"data: {chunk['response']}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
