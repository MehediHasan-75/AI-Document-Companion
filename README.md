# AI Document Companion

A **RAG-powered document intelligence system** that lets you upload documents and have natural conversations with their content. Built with FastAPI, LangChain, and local LLMs via Ollama.

## What It Does

Upload a PDF, and this system will:
1. **Parse** the document into text, tables, and images using intelligent partitioning
2. **Summarize** each element with AI (Deepseek for text/tables, Llava for images)
3. **Store** embeddings in a vector database for semantic search
4. **Answer questions** about your documents using RAG

Think of it as your personal document assistant that actually understands what's in your files.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                          │
├─────────────────────────────────────────────────────────────────┤
│  Routes: /files/upload → /files/process → /query/ask            │
├─────────────────────────────────────────────────────────────────┤
│                      Ingestion Pipeline                          │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐    │
│  │ Unstructured │→ │ LLM Summarize │→ │ ChromaDB + Docstore│    │
│  │  (Parsing)   │  │ (Deepseek/    │  │   (Vector Store)   │    │
│  │              │  │   Llava)      │  │                    │    │
│  └──────────────┘  └───────────────┘  └────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                       RAG Query Engine                           │
│  User Question → Semantic Search → Context Retrieval → LLM Answer│
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI | REST endpoints, async processing |
| **Document Parsing** | Unstructured | Extract text, tables, images from PDFs |
| **LLM Inference** | Ollama (Deepseek-R1, Llava) | Local summarization & RAG responses |
| **Embeddings** | HuggingFace (all-MiniLM-L6-v2) | Sentence embeddings for semantic search |
| **Vector Store** | ChromaDB | Persistent similarity search |
| **Orchestration** | LangChain | RAG chains & prompt management |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/files/upload` | Upload a single document |
| `POST` | `/files/upload/multiple` | Batch upload multiple files |
| `POST` | `/files/process/{file_id}` | Trigger document ingestion (async) |
| `GET` | `/files/status/{file_id}` | Check processing status |
| `POST` | `/query/ask` | Ask questions about your documents |
| `DELETE` | `/files/delete?file_id=` | Remove a document |

## Getting Started

### Prerequisites

**macOS:**
```bash
brew install libmagic poppler tesseract
```

**Ollama (Local LLM Server):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:8b
ollama pull llava
```

### Installation

```bash
# Clone and setup
git clone <repo-url>
cd ai-document-companion

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Server

```bash
# Start Ollama first (in a separate terminal)
ollama serve

# Start the API server
uvicorn main:app --reload
```

Visit **http://localhost:8000/docs** for interactive API documentation.

## Usage Example

```bash
# 1. Upload a document
curl -X POST "http://localhost:8000/files/upload" \
  -F "file=@document.pdf"
# Returns: {"file_id": "abc123..."}

# 2. Process the document
curl -X POST "http://localhost:8000/files/process/abc123"

# 3. Check status (wait for completion)
curl "http://localhost:8000/files/status/abc123"

# 4. Ask questions
curl -X POST "http://localhost:8000/query/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings in this document?"}'
```

## Project Structure

```
src/
├── routes/          # API endpoints
├── controllers/     # Request handling logic
├── services/        # Core business logic
│   ├── ingestion_service.py    # Document processing pipeline
│   ├── llm_service.py          # LLM chains (summarization, RAG)
│   ├── vector_service.py       # ChromaDB & embeddings
│   └── unstructured_service.py # PDF parsing
├── models/          # Database models
├── repositories/    # Data access layer
└── schemas/         # Pydantic models
```

## Key Design Decisions

- **Local-first**: Uses Ollama for LLM inference—no API keys or cloud dependencies
- **Multi-modal**: Handles text, tables, and images from documents
- **Async processing**: Document ingestion runs in background tasks
- **Multi-vector retrieval**: Searches on summaries, retrieves original content
- **Clean architecture**: Separation of routes → controllers → services

## Future Roadmap

- [ ] Redis caching for LLM responses
- [ ] WebSocket streaming for real-time answers
- [ ] Message queue for distributed processing
- [ ] Additional file format support (DOCX, PPTX)
- [ ] Conversation history & memory

## License

MIT License — see [LICENSE](LICENSE)
