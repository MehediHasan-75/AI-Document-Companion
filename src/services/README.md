# Services Layer

Core business logic for the AI Document Companion RAG pipeline.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            Services Layer                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│   │  file_service   │────▶│ process_service │────▶│ingestion_service│   │
│   │  (Upload/Store) │     │  (Orchestrate)  │     │   (Pipeline)    │   │
│   └─────────────────┘     └─────────────────┘     └─────────────────┘   │
│                                                            │             │
│                           ┌────────────────────────────────┼─────┐       │
│                           │                                ▼     │       │
│   ┌─────────────────┐     │  ┌─────────────────┐  ┌─────────────────┐   │
│   │   rag_chain     │◀────┼──│retrieval_service│◀─│  vector_service │   │
│   │  (LCEL Chain)   │     │  │ (Multi-Vector)  │  │ (ChromaDB/Store)│   │
│   └────────┬────────┘     │  └─────────────────┘  └─────────────────┘   │
│            │               │                                             │
│            ▼               │                                             │
│   ┌─────────────────┐     │                                             │
│   │streaming_service│     │                                             │
│   │(Streaming + Conv)│     │                                             │
│   └─────────────────┘     │                                             │
│           │               │           ▲                    ▲             │
│           │               │           │                    │             │
│           ▼               │  ┌─────────────────┐  ┌─────────────────┐   │
│   ┌─────────────────┐     │  │  chunk_service  │  │unstructured_svc │   │
│   │   llm_service   │     │  │ (Separate/B64)  │  │  (PDF Parsing)  │   │
│   │ (Deepseek/Llava)│     │  └─────────────────┘  └─────────────────┘   │
│   └─────────────────┘     │                                             │
│                           └─────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────────────────────┘
```

## Service Descriptions

| Service | File | Responsibility |
|---------|------|----------------|
| **FileService** | `file_service.py` | Upload, store, delete files; generate UUIDs |
| **ProcessService** | `process_service.py` | Orchestrate ingestion; track status (uploaded→processing→processed/failed) |
| **IngestionService** | `ingestion_service.py` | Full document pipeline: parse → summarize → embed → store |
| **RagChain** | `rag_chain.py` | Build LCEL chain: retrieve → resolve originals → prompt → LLM |
| **VectorService** | `vector_service.py` | Manage ChromaDB (embeddings) and SimpleDocStore (originals) |
| **RetrievalService** | `retrieval_service.py` | Multi-vector retrieval: search summaries, return originals |
| **LLMService** | `llm_service.py` | Chains for summarization (deepseek-r1), QA (llava), and image description (llava) |
| **ChunkService** | `chunk_service.py` | Separate elements by type; extract base64 images |
| **UnstructuredService** | `unstructured_service.py` | PDF parsing with hi_res strategy |
| **StreamingService** | `streaming_service.py` | Token-by-token SSE streaming for conversation /ask |

## Document Processing Flow

```
1. UPLOAD
   POST /files/upload
   └── file_service.save_upload(file) → file_id

2. PROCESS (async)
   POST /files/process/{file_id}
   └── process_service.process_file_async()
       ├── Status: "processing"
       └── BackgroundTask: _run_pipeline()

3. INGESTION PIPELINE (background)
   ingest_document_pipeline(file_path)
   ├── unstructured_service.partition_document()  → chunks
   ├── chunk_service.separate_elements()          → texts, tables
   ├── chunk_service.get_images_base64()          → images
   ├── llm_service.get_text_table_summarizer()    → text summaries
   ├── llm_service.get_image_summarizer()         → image summaries
   ├── vector_service.get_vectorstore()           → ChromaDB
   ├── vector_service.get_docstore()              → SimpleDocStore
   └── retrieval_service.add_documents_to_retriever()
       ├── Embed summaries → ChromaDB
       └── Store originals → docstore.db

4. STATUS UPDATE
   └── process_service._write_status() → "processed" or "failed"
```

## Streaming Chat Flow

```
POST /conversations/{id}/ask {"question": "..."}

streaming_service.stream_chat_response()
├── Validate conversation ownership
├── Load chat history from DB (last 20 messages)
├── Save user message
├── Retrieve context
│   ├── retriever → MMR search (fetch 20, return 5)
│   ├── resolve_originals() → swap summaries for originals
│   └── parse_docs() → separate images from text
├── Build prompt (context + history + question)
├── llm.astream(messages) → stream tokens as SSE
│   └── yield {"type": "delta", "content": "..."} per token
├── Save assistant message + sources to DB
└── yield {"type": "complete", "content": "...", "sources": [...]}
```

## Status Tracking

ProcessService tracks file state in `uploads/status/{file_id}.json`:

```json
{"file_id": "abc-123", "status": "processed"}
```

State machine:
```
uploaded ──▶ processing ──▶ processed
                       └──▶ failed (includes error message)
```

## Configuration

Services read from `src/config/settings` (singleton):

```python
from src.config import settings

settings.OLLAMA_HOST        # http://localhost:11434
settings.OLLAMA_MODEL       # deepseek-r1:8b
settings.EMBEDDING_MODEL    # sentence-transformers/all-MiniLM-L6-v2
```

## Integration Points (Future)

Each service has placeholder comments for:

- **REDIS_INTEGRATION**: Distributed caching, status storage
- **WEBSOCKET_INTEGRATION**: Real-time status updates, streaming responses
- **MQ_INTEGRATION**: Message queue for async job processing

## Usage Examples

```python
# Direct service usage
from src.services import file_service, process_service

# Upload
file_id = file_service.save_upload(uploaded_file)

# Process (async, via BackgroundTasks)
process_service.process_file_async(file_id, background_tasks, user_id=user_id)
```
