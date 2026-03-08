# services/query_service.py
from core.embeddings import embedding_model
from core.vectorstore import retriever
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

llm = ChatOllama(model="deepseek-r1:8b", temperature=0.7)

async def query_rag(question: str, top_k: int = 5):
    # 1️⃣ Embed question
    q_vector = embedding_model.embed_query(question)

    # 2️⃣ Retrieve relevant chunks
    docs = retriever.similarity_search_vector(q_vector, k=top_k)

    # 3️⃣ Combine context
    context_text = "\n\n".join(docs)

    # 4️⃣ Ask LLM
    response = llm.invoke([
        HumanMessage(content=f"Answer using the following context:\n{context_text}\n\nQuestion: {question}")
    ])

    return response.content