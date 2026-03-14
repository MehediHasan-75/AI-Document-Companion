<div align="center">

# AI Document Companion

**A production-grade multimodal RAG pipeline. Upload PDFs, Word documents, spreadsheets, and presentations. Ask questions. Get answers grounded in sources — with persistent, user-scoped conversation memory.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-LCEL-1C3C3C?style=flat-square&logo=chainlink&logoColor=white)](https://python.langchain.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B35?style=flat-square)](https://www.trychroma.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## What This Is

Most RAG demos chunk plain text and call it multimodal. This pipeline handles the hard cases: PDFs with embedded tables, scanned diagrams, Word documents with mixed content. It separates text, structured tables (as HTML), and images at the element level using ML-based layout detection — then summarises each type with the appropriate model before indexing.

The architecture is intentionally layered. Every design decision has a concrete reason documented below.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUEST                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI  (src/main.py)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │    CORS     │  │    GZip     │  │  Request Logger (http) │  │
│  │ Middleware  │  │ Middleware  │  │  method · path · ms    │  │
│  └─────────────┘  └─────────────┘  └────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┼───────────────┐
          ▼           ▼               ▼
   ┌─────────────┐ ┌────────┐ ┌─────────────────┐
   │ auth_routes │ │ files  │ │  conversations  │
   │  /register  │ │/upload │ │  /ask  /list    │
   │  /login /me │ │/process│ └────────┬────────┘
   └──────┬──────┘ └───┬────┘          │
          │            │               │
          ▼            ▼               ▼
   ┌─────────────────────────────────────────────┐
   │               CONTROLLERS                   │
   │   auth · file · process · query · convo     │
   └───────────┬─────────────────────────────────┘
               │
   ┌───────────┼──────────────────────────────────┐
   ▼           ▼              ▼                   ▼
┌──────┐  ┌─────────┐  ┌───────────┐  ┌──────────────────┐
│ Auth │  │ File /  │  │  RAG      │  │  Conversation    │
│ Svc  │  │ Process │  │  Pipeline │  │  Service         │
│      │  │ Service │  │           │  │  (memory store)  │
└──┬───┘  └────┬────┘  └─────┬─────┘  └────────┬─────────┘
   │           │             │                  │
   ▼           ▼             ▼                  ▼
┌──────────────────┐   ┌───────────────┐  ┌────────────────┐
│  PostgreSQL /    │   │ Chroma (vecs) │  │  SQLite        │
│  SQLite          │   │ + DocStore    │  │  (messages /   │
│  users · convos  │   │   (SQLite)    │  │  conversations)│
│  messages·chunks │   └───────────────┘  └────────────────┘
└──────────────────┘


                    INGESTION PIPELINE
┌────────────────────────────────────────────────────────────┐
│  File Upload                                               │
│       │                                                    │
│       ▼                                                    │
│  unstructured.partition() ── hi_res ML layout detection    │
│       │                                                    │
│       ▼                                                    │
│  chunk_by_title()  ◄── structural chunking (not char-split)│
│       │                                                    │
│  ┌────┴──────────────────┐                                 │
│  ▼           ▼           ▼                                 │
│ texts      tables      images                              │
│            (HTML via   (base64 from                        │
│           text_as_html) orig_elements)                     │
│  └────┬──────────────────┘                                 │
│       ▼                                                    │
│  LLM Summarization  (batch, max_concurrency=3)             │
│       │                                                    │
│  ┌────┴──────────────────┐                                 │
│  ▼                       ▼                                 │
│ Summaries ──────► Chroma (all-MiniLM-L6-v2, 384-dim)      │
│ Originals ──────► SQLite DocStore  (WAL mode)              │
└────────────────────────────────────────────────────────────┘
```

---

## Technical Deep Dive

<details>
<summary><strong>Why Unstructured for Multimodal Parsing</strong></summary>

<br>

The core problem with PDF parsing is that a file's byte stream encodes visual layout, not semantic structure. A naive approach — read text with `pdfminer`, split on newlines — loses table cell boundaries, ignores embedded images entirely, and merges headers with body text.

`unstructured` solves this with `partition(strategy="hi_res")` which runs an ML-based document layout model to classify page regions before extracting them. The pipeline receives back typed `Element` objects rather than a flat string:

```python
# src/services/unstructured_service.py
elements = partition(
    filename=file_path,
    strategy="hi_res",             # ML layout detection, not rule-based
    infer_table_structure=True,    # returns table.metadata.text_as_html
    pdf_extract_image_block_types=["Image"],
    pdf_extract_image_block_to_payload=True,  # base64 in metadata
)
```

The chunk separation step (`src/services/chunk_service.py`) then routes by element type:

```python
def separate_elements(chunks):
    for chunk in chunks:
        if "Table" in str(type(chunk)):
            tables.append(chunk)        # → table.metadata.text_as_html
        if "CompositeElement" in str(type(chunk)):
            texts.append(chunk)         # → plain text

def get_images_base64(chunks):
    for chunk in chunks:
        for el in chunk.metadata.orig_elements:
            if "Image" in str(type(el)):
                images_b64.append(el.metadata.image_base64)
```

Each content type then hits the appropriate summariser: text and HTML tables go to `deepseek-r1:8b`; images go to `llava` via a vision prompt with base64 image_url content.

**Single `partition()` call handles:** PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, HTML, JSON — no format-specific code paths.

</details>

<details>
<summary><strong>Multi-Vector Retrieval Architecture</strong></summary>

<br>

Standard RAG embeds raw document chunks and retrieves by cosine similarity. This creates a recall problem: a user question phrased naturally often has low cosine similarity to a dense technical paragraph even when that paragraph contains the answer.

This pipeline uses a **multi-vector strategy**: what gets embedded in Chroma is an LLM-generated summary. What gets stored in the docstore is the original.

```
Ingestion:
  raw_chunk → LLM → summary → embed → Chroma  (metadata: {doc_id, type})
  raw_chunk ──────────────────────── DocStore  (keyed by doc_id)

Query:
  question → embed → Chroma similarity search → [summary docs with doc_ids]
                                                        │
                                           docstore.get(doc_id) → original
                                                        │
                                             injected into LLM prompt
```

The LLM's answer is grounded in the **original content**, retrieved via the **summary's embedding space** — which is semantically closer to how a user phrases a natural question.

The `chain_with_sources` LCEL chain carries `context` through the pipeline so the sources returned to the API are the exact documents the LLM used — not a separate retrieval call:

```python
# src/services/rag_chain.py
chain_with_sources = setup_and_retrieval | RunnablePassthrough().assign(
    response=(RunnableLambda(build_prompt) | llm | StrOutputParser())
)
# result["context"]["texts"]  == exactly what the LLM received
# result["response"]          == the answer
```

Image documents are routed by `doc.metadata["type"] == "image"` (set at ingestion) — not by attempting `b64decode` on content strings, which silently succeeds on many plain-text values.

</details>

<details>
<summary><strong>Chunking Strategy and Token Efficiency Trade-offs</strong></summary>

<br>

**`chunk_by_title` vs `RecursiveCharacterTextSplitter`**

`RecursiveCharacterTextSplitter` operates on character count. It is document-format-agnostic, which is a liability for structured documents — it will cut across a table row mid-cell or split a bullet list mid-item to satisfy a token budget.

`chunk_by_title` uses the heading hierarchy extracted by Unstructured's layout model. Each chunk contains a complete logical unit and never splits across a structural boundary.

**The constants are deliberate:**

```python
# src/config/constants.py
DEFAULT_MAX_CHARACTERS      = 10000  # ceiling per chunk
DEFAULT_COMBINE_UNDER_N_CHARS = 2000  # merge short sections with the next
DEFAULT_NEW_AFTER_N_CHARS   = 6000   # soft split after 6k chars
```

`COMBINE_UNDER_N_CHARS=2000` prevents fragmenting short one-paragraph sections into isolated chunks — a common cause of low-recall retrieval. `NEW_AFTER_N_CHARS=6000` keeps sections below the token limit for summarisation without hard-cutting at a fixed byte offset.

**Why summaries improve embedding quality**

`all-MiniLM-L6-v2` has a 256-token sequence limit. Raw 6000-character chunks get silently truncated before embedding, losing the tail of the section entirely. LLM-generated summaries are typically 50–150 tokens — fully within the model's effective range and semantically denser.

**Trade-off accepted:** Summarisation adds one LLM call per chunk at ingestion time. For a 50-page document with 40 chunks, that is 40 LLM calls batched at `max_concurrency=3`. This is a deliberate write-time cost to improve read-time retrieval quality.

**Conversation memory budget:** The last 20 messages are injected into the prompt (`MAX_HISTORY_MESSAGES = 20` in `conversation_service.py`). This is a hard sliding window rather than a rolling summary — simpler to reason about, at the cost of losing older context on very long conversations.

</details>

<details>
<summary><strong>Stateless LLM Memory via Database</strong></summary>

<br>

LLMs are stateless: every call is independent. Multi-turn conversation requires replaying context on every request. The design decision is *where* to store it and *how much* to inject.

This pipeline uses explicit DB-backed memory rather than LangChain's `RunnableWithMessageHistory`. The reason: `SQLChatMessageHistory` creates its own flat schema and has no concept of user ownership, message sources, or soft-delete. Building on top of it requires a parallel storage system to maintain those properties.

Instead, `ConversationService` manages the full lifecycle:

```python
# src/services/conversation_service.py

# On every /conversations/{id}/ask:
history = conversation_service.get_history(db, conversation_id, user_id=user_id)
# → SELECT last 20 messages WHERE conversation_id = ? AND user_id = ?
# → returned as [{"role": "user", "content": "..."}, ...]

# Injected into the RAG prompt:
# "Conversation history:\nUser: ...\nAssistant: ..."

# Both turns persisted after LLM responds:
conversation_service.add_message(db, ..., role=USER,      content=question)
conversation_service.add_message(db, ..., role=ASSISTANT, content=answer, sources=sources)
```

**User-scoped isolation:** Every conversation query filters by `user_id`. Enforced at the service layer, not just the route.

**Sources stored per message:** Each assistant `Message` row carries a `sources: JSON` column containing the `doc_id`, `summary`, and `type` of every chunk the LLM used. This creates a per-response audit trail retrievable via `GET /conversations/{id}/messages`.

</details>

<details>
<summary><strong>Authentication and Security Design</strong></summary>

<br>

JWT-based auth using `python-jose` (HS256, 24-hour expiry) with `bcrypt` for password hashing — using the `bcrypt` library directly rather than `passlib`, which breaks on Python 3.12 with bcrypt 4.x due to an unmaintained C binding.

The dependency graph for any protected route:

```
Route handler
    └── current_user: User = Depends(get_current_user)   [dependencies/auth.py]
              └── token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login"))
              └── db: Session = Depends(get_db)           [dependencies/db.py]
              └── decode_token(token) → payload["sub"] = user_id
              └── auth_service.get_by_id(db, user_id) → User
```

`get_current_user` lives in `src/dependencies/auth.py`. Swapping to RS256 or an external identity provider touches one file, not every route.

Each exception subclass declares its own HTTP status code:

```python
# src/core/exceptions.py
class AuthenticationError(AppError):
    status_code = 401

class ConflictError(AppError):
    status_code = 409
```

The global handler reads `exc.status_code` directly — no lookup table, no imports of individual exception classes in `main.py`.

</details>

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | — | Register. Returns `UserResponse`. |
| `POST` | `/auth/login` | — | Login (form: `username`, `password`). Returns JWT. |
| `GET` | `/auth/me` | ✓ | Current authenticated user. |
| `POST` | `/files/upload` | ✓ | Upload a single document. Returns `file_id`. |
| `POST` | `/files/upload/multiple` | ✓ | Batch upload. Returns per-file results. |
| `POST` | `/files/process/{file_id}` | ✓ | Trigger async ingestion pipeline. |
| `GET` | `/files/status/{file_id}` | ✓ | Poll ingestion status (`uploaded` / `processing` / `processed` / `failed`). |
| `DELETE` | `/files/delete` | ✓ | Delete a document by `file_id`. |
| `POST` | `/query/ask` | ✓ | Stateless RAG query. Returns answer + sources. |
| `POST` | `/conversations` | ✓ | Create a conversation. |
| `GET` | `/conversations` | ✓ | List your conversations. |
| `POST` | `/conversations/{id}/ask` | ✓ | Ask with full conversation history injected. |
| `GET` | `/conversations/{id}/messages` | ✓ | Retrieve message history with sources. |
| `DELETE` | `/conversations/{id}` | ✓ | Soft-delete a conversation. |

Interactive docs at `http://localhost:8000/docs` — the Swagger UI **Authorize** button is wired to the JWT bearer flow.

---

## Setup

### Prerequisites

```bash
# macOS — required by Unstructured hi_res strategy
brew install libmagic poppler tesseract

# Ollama — local LLM runtime
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:8b   # text LLM
ollama pull llava             # vision LLM (image summarisation)
```

### Install

```bash
git clone https://github.com/MehediHasan-75/AI-Document-Companion.git
cd AI-Document-Companion

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Minimum required changes:

```env
# Generate with: openssl rand -hex 32
SECRET_KEY=your-secret-key-here

# SQLite works out of the box for development
DATABASE_URL=sqlite:///./app.db
```

### Run

```bash
uvicorn main:app --reload
```

API at `http://localhost:8000` · Swagger UI at `http://localhost:8000/docs`

### Typical Workflow

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'

# 2. Login — capture token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -F "username=you@example.com" -F "password=yourpassword" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Upload a document
FILE_ID=$(curl -s -X POST http://localhost:8000/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['file_id'])")

# 4. Trigger ingestion (runs in background)
curl -X POST http://localhost:8000/files/process/$FILE_ID \
  -H "Authorization: Bearer $TOKEN"

# 5. Poll until "processed"
curl http://localhost:8000/files/status/$FILE_ID \
  -H "Authorization: Bearer $TOKEN"

# 6. Stateless query
curl -X POST http://localhost:8000/query/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main findings?"}'

# 7. Or start a conversation with persistent memory
CONV_ID=$(curl -s -X POST http://localhost:8000/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -X POST http://localhost:8000/conversations/$CONV_ID/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarise the methodology section."}'
```

---

## Project Structure

```
.
├── main.py                         # Uvicorn entrypoint — re-exports src.main:app
├── requirements.txt
├── .env.example
└── src/
    ├── main.py                     # FastAPI app, middleware stack, exception handlers
    ├── config/
    │   ├── constants.py            # Chunk sizes, retrieval K, model names
    │   ├── environment.py          # Pydantic Settings (all env vars typed)
    │   ├── file_types.py           # Allowed MIME types (frozenset)
    │   └── prompts.py              # LLM prompt templates
    ├── core/
    │   ├── exceptions.py           # Exception hierarchy — each class owns status_code
    │   └── logger.py
    ├── db/
    │   ├── base.py                 # SQLAlchemy Base, UUIDMixin, TimestampMixin
    │   └── session.py              # Engine factory, SessionLocal, init_db
    ├── dependencies/
    │   ├── auth.py                 # get_current_user (JWT decode → User ORM object)
    │   └── db.py                   # get_db (request-scoped SQLAlchemy session)
    ├── models/
    │   ├── user.py                 # User (email, hashed_password, is_active)
    │   ├── document.py             # Document (status lifecycle, doc_type enum)
    │   ├── chunk.py                # Chunk (vector_id FK into Chroma, summary)
    │   ├── conversation.py         # Conversation (user_id scoped, soft-delete)
    │   └── message.py              # Message (role enum, content, sources JSON)
    ├── schemas/
    │   ├── auth.py                 # RegisterRequest, TokenResponse, UserResponse
    │   ├── query.py                # QueryRequest
    │   └── conversation.py         # CreateConversationRequest, ChatRequest
    ├── routes/
    │   ├── index.py                # Single aggregation point for all routers
    │   ├── auth_routes.py
    │   ├── file_routes.py
    │   ├── process_routes.py
    │   ├── query_routes.py
    │   └── conversation_routes.py
    ├── controllers/                # Orchestration between routes and services
    └── services/
        ├── auth_service.py         # bcrypt hashing, JWT issue/verify
        ├── file_service.py         # MIME + size validation, streaming chunked write
        ├── process_service.py      # Background task dispatch, status file tracking
        ├── ingestion_service.py    # Full pipeline: partition → summarise → index
        ├── unstructured_service.py # partition() with hi_res + chunk_by_title()
        ├── chunk_service.py        # Route CompositeElement / Table / Image
        ├── llm_service.py          # Singleton ChatOllama (text + vision)
        ├── rag_chain.py            # LCEL chain construction, build_prompt, parse_docs
        ├── retrieval_service.py    # Multi-vector retriever, add_documents_to_retriever
        ├── vector_service.py       # Chroma singleton + SQLite DocStore (WAL)
        ├── query_service.py        # ask_with_sources — single retrieval via chain_with_sources
        └── conversation_service.py # Message CRUD, 20-message sliding window history
```

---

## Supported Document Types

| Format | MIME Type | Notes |
|--------|-----------|-------|
| PDF | `application/pdf` | Tables, images, text via `hi_res` layout detection |
| Word | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Styles-aware parsing |
| PowerPoint | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | Slide-by-slide |
| Excel | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Sheets extracted as tables |
| CSV | `text/csv` | Tabular |
| Markdown | `text/markdown` | Heading hierarchy preserved |
| HTML | `text/html` | |
| Plain text | `text/plain` | |
| JSON | `application/json` | |

---

<div align="center">
  <sub>Built by <a href="https://github.com/MehediHasan-75">Mehedi Hasan</a></sub>
</div>
