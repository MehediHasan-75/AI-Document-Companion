# services/ingestion_service.py
import asyncio
import logging
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

# from core.embeddings import embedding_model
# from core.vectorstore import retriever
from services.chunking import ChunkingService, HiResStrategy

logger = logging.getLogger(__name__)

# ── LLM setup ──────────────────────────────────────────────────────────────────
# Text-only model for summarising text + tables
llm_text = ChatOllama(model="deepseek-r1:8b", temperature=0.3)

# Multimodal model for image captioning (must support vision)
llm_image = ChatOllama(model="llava", temperature=0.3)

# ── Chunking service ────────────────────────────────────────────────────────────
chunking_service = ChunkingService(strategy=HiResStrategy)


# ── Summarisation helpers ───────────────────────────────────────────────────────

async def _summarize_text(text: str) -> str:
    """Summarise a text or table block."""
    resp = await asyncio.to_thread(
        llm_text.invoke,
        [HumanMessage(content=f"Summarize this content concisely:\n{text}")]
    )
    return resp.content


async def _caption_image(image_b64: str) -> str:
    """Generate a caption for a base64-encoded image using a vision model."""
    resp = await asyncio.to_thread(
        llm_image.invoke,
        [HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": f"data:image/png;base64,{image_b64}",
            },
            {
                "type": "text",
                "text": "Describe this image in detail, focusing on key content and figures.",
            },
        ])]
    )
    return resp.content


# ── Main ingestion entry point ──────────────────────────────────────────────────

async def process_pdf(file_path: str) -> dict:
    """
    Partition a PDF, summarise all modalities, embed, and store in Qdrant.

    Returns a summary dict with counts of processed chunks.
    """

    # 1️⃣  Partition into typed chunks
    result = chunking_service.process(file_path)
    logger.info("Partitioned: %s", result)

    # 2️⃣  Summarise all modalities concurrently
    text_tasks  = [_summarize_text(c.text) for c in result.text_chunks]
    table_tasks = [_summarize_text(t.html or t.text) for t in result.table_chunks]
    image_tasks = [_caption_image(i.image_b64) for i in result.image_chunks]

    text_summaries, table_summaries, image_captions = await asyncio.gather(
        asyncio.gather(*text_tasks),
        asyncio.gather(*table_tasks),
        asyncio.gather(*image_tasks),
    )

    # 3️⃣  Combine all summaries
    all_summaries = [*text_summaries, *table_summaries, *image_captions]

    # 4️⃣  Embed & store in Qdrant
    for summary in all_summaries:
        if not summary.strip():
            continue
        vector = embedding_model.embed_query(summary)
        retriever.add_texts([summary], [vector])

    counts = {
        "texts":          len(result.text_chunks),
        "tables":         len(result.table_chunks),
        "images":         len(result.image_chunks),
        "stored_vectors": len(all_summaries),
    }
    logger.info("Ingestion complete: %s", counts)
    return counts