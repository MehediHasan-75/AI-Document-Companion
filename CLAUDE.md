# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Document Companion — a multimodal RAG (Retrieval-Augmented Generation) pipeline built with FastAPI, LangChain, and Ollama. Ingests documents (PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, HTML, JSON), creates vector embeddings of LLM-generated summaries, and provides conversational Q&A with persistent chat history.

## Commands

```bash
# Run development server
source .venv/bin/activate
uvicorn src.main:app --reload

# Install dependencies
pip install -r requirements.txt

# System dependencies (macOS)
brew install libmagic poppler tesseract

# Pull required Ollama models
ollama pull deepseek-r1:8b   # text LLM (summarization + QA)
ollama pull qwen3-vl:8b      # vision LLM (image summarization)
```

API docs at http://localhost:8000/docs (Swagger UI with JWT auth flow).

No test suite, linter, or formatter is currently configured.

## Architecture

**Layered structure:** Routes → Services, with FastAPI dependency injection for DB sessions and auth.

```
src/
  main.py                        # FastAPI app, middleware, exception handlers, startup (init_db)
  routes/index.py                # Aggregates all route modules
  routes/{auth,file,process,conversation}_routes.py
  services/                      # All business logic lives here
  models/                        # SQLAlchemy ORM models (User, Document, Chunk, Conversation, Message)
  schemas/                       # Pydantic request/response models
  config/
    environment.py               # Pydantic Settings with .env loading
    constants.py                 # Tunable constants (chunk sizes, retrieval K, temperatures)
    prompts.py                   # All LLM prompt templates
    file_types.py                # ALLOWED_CONTENT_TYPES frozenset
  dependencies/
    auth.py                      # get_current_user (JWT decode → User ORM)
    db.py                        # get_db (request-scoped SQLAlchemy session)
```

### Key Design Decisions

- **Multi-vector retrieval:** LLM-generated summaries are embedded in ChromaDB; original content is stored in a SQLite docstore. Queries match against summary vectors, then retrieve originals for the LLM context.
- **Document parsing:** Single `unstructured.partition(strategy="hi_res")` call handles all formats — no format-specific code paths. Chunking uses `chunk_by_title()` (structural) not character-based splitting.
- **Singleton LLM/vectorstore instances:** `llm_service.py` and `vector_service.py` use module-level singletons with lazy initialization to avoid per-request connection overhead.
- **SQLite docstore with WAL mode:** Replaced JSON file docstore (`SimpleDocStore` in `vector_service.py`) for O(1) writes and safe concurrent access.
- **Exception hierarchy:** Each error subclass in `src/exceptions/` declares its own `status_code` attribute — no lookup table. Global handler in `src/main.py` reads it directly.
- **Async ingestion:** `BackgroundTasks.add_task()` for non-blocking document processing. Status tracked via JSON files in `uploads/status/{file_id}.json`.
- **Conversation memory:** DB-backed (not LangChain's `RunnableWithMessageHistory`). 20-message sliding window injected into RAG prompt. Sources stored per assistant message.
- **Streaming conversation responses:** `POST /conversations/{id}/ask` streams tokens via SSE using `streaming_service.py`. Retrieval is non-streamed; only LLM generation is streamed via `llm.astream()`.

### RAG Pipeline Flow

1. **Ingest:** `partition()` → `chunk_by_title()` → separate text/tables/images → LLM summarize each (max_concurrency=3) → embed summaries in Chroma + store originals in docstore
2. **Query:** User question → similarity search on summary vectors (K=5) → retrieve originals from docstore → build prompt with context + chat history → stream LLM response token-by-token via SSE

### Auth Flow

Register → bcrypt hash → JWT issued (HS256, 24h expiry). Protected routes use `Depends(get_current_user)`. All data is user-scoped at the service layer.

### Database

SQLAlchemy 2.0+ with SQLite (dev) or PostgreSQL (prod). Tables auto-created on startup via `init_db()`. Models: User, Document, Chunk, Conversation, Message.

**`Document` metadata fields:** `file_size` (bytes), `page_count`, `chunk_count` (total, stored on mark_processed), `status`, `error_message`, `processed_at`.

**`Chunk` types:** `text`, `table`, `image`, `code`, `heading` (via `ChunkType` enum). `image_count` and `table_count` are derived at query time via a single GROUP BY on the chunks table — not stored on Document — so they always reflect the live chunk records.

### `/files` List Response

`GET /files` returns `FileItem` objects with: `id`, `filename`, `status`, `created_at`, `type`, `file_size`, `page_count`, `chunk_count`, `image_count`, `table_count`. Counts are `null` for unprocessed files. Image/table counts use one extra aggregation query (not N+1).
