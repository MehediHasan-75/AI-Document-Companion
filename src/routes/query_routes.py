# routes/query_route.py
from fastapi import APIRouter
# from services.query_service import query_rag

router = APIRouter()

@router.get("/ask")
async def ask(question: str):
    answer = await query_rag(question)
    return {"answer": answer}