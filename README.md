# AI Document Companion

A **RAG-powered document intelligence system** that lets you upload documents and have natural conversations with their content. Built with **FastAPI**, **LangChain**, and **local LLMs via Ollama**.

---

## What It Does

Upload a PDF, and this system will:
1. **Parse** the document into text, tables, and images using intelligent partitioning
2. **Summarize** each element with AI (Deepseek for text/tables, Llava for images)
3. **Store** summary embeddings in a vector database for semantic search
4. **Answer questions** about your documents using a multi-modal RAG chain

Think of it as your personal document assistant that actually understands what's in your files.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          FastAPI Server                               │
├──────────────────────────────────────────────────────────────────────┤
│  Routes: /files/upload  →  /files/process/{id}  →  /query/ask        │
├──────────────────────────────────────────────────────────────────────┤
│                       Ingestion Pipeline                              │
│  ┌───────────────┐   ┌────────────────────┐   ┌──────────────────┐   │
│  │ Unstructured  │──▶│ LangChain Chains   │──▶│ ChromaDB (vector)│   │
│  │  (Partition)  │   │ (Summarize via LLM)│   │ DocStore (JSON)  │   │
│  └───────────────┘   └────────────────────┘   └──────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│                       RAG Query Engine                                │
│  Question ──▶ VectorStoreRetriever ──▶ RunnableChain ──▶ LLM Answer  │
│                   (LangChain)            (LCEL)          (Ollama)     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI | REST endpoints, async background processing |
| **Document Parsing** | Unstructured | Extract text, tables, images from PDFs |
| **LLM Inference** | Ollama (Deepseek-R1, Llava) | Local summarization and RAG responses |
| **Embeddings** | LangChain HuggingFaceEmbeddings | Sentence embeddings for semantic search |
| **Vector Store** | LangChain Chroma integration | Persistent similarity search |
| **RAG Orchestration** | LangChain LCEL (Runnables) | Chain composition, prompt management |
| **Database** | SQLAlchemy 2.0 | Document metadata, conversations, messages |

---

## How LangChain Powers This Project

This project uses **LangChain extensively** across six major packages to build a production-grade RAG pipeline. Nothing is done manually — every LLM interaction, embedding, retrieval, and chain composition goes through LangChain's framework.

### LangChain Packages Used

```
langchain-core        →  LCEL runnables, prompts, output parsers, base document model
langchain-ollama      →  ChatOllama LLM wrapper for local model inference
langchain-chroma      →  Chroma vector store integration
langchain-huggingface →  HuggingFaceEmbeddings for sentence-transformers
langchain-openai      →  OpenAI embeddings (available as alternative)
langchain-community   →  Community integrations
```

---

### 1. LLM Integration — `ChatOllama` (langchain-ollama)

> **File:** `src/services/llm_service.py`, `src/services/rag_chain.py`

Instead of calling Ollama's REST API manually, the project uses LangChain's `ChatOllama` wrapper. This gives us a standardized `BaseChatModel` interface that plugs directly into LangChain chains.

```python
from langchain_ollama import ChatOllama

# Text/table summarization LLM
def _get_text_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.OLLAMA_MODEL,       # "deepseek-r1:8b"
        base_url=settings.OLLAMA_HOST,     # "http://localhost:11434"
        temperature=SUMMARIZATION_TEMPERATURE,
    )

# Vision LLM for image understanding
def _get_vision_llm() -> ChatOllama:
    return ChatOllama(
        model=VISION_MODEL,                # "llava"
        base_url=settings.OLLAMA_HOST,
        temperature=VISION_TEMPERATURE,
    )
```

**Why LangChain here?** `ChatOllama` implements the `BaseChatModel` interface, so we can swap it with `ChatOpenAI`, `ChatGroq`, or any other provider without changing any downstream chain logic. The model is interchangeable — the chains stay the same.

---

### 2. Prompt Engineering — `ChatPromptTemplate` (langchain-core)

> **File:** `src/services/llm_service.py`, `src/config/prompts.py`

All prompts are built using LangChain's `ChatPromptTemplate`, not raw string formatting. This ensures proper message structure, variable injection, and compatibility with any LLM.

```python
from langchain_core.prompts import ChatPromptTemplate

# Text/table summarization chain using ChatPromptTemplate
prompt = ChatPromptTemplate.from_template("""
You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.
Table or text chunk: {element}
""")

# Multi-modal image prompt with structured message format
messages = [
    ("user", [
        {"type": "text", "text": IMAGE_SUMMARIZATION_PROMPT},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{image}"}},
    ])
]
prompt = ChatPromptTemplate.from_messages(messages)
```

**Why LangChain here?** `ChatPromptTemplate` handles variable substitution (`{element}`, `{image}`), supports multi-modal content blocks (text + images), and formats messages correctly for the chat model API. No manual string interpolation or message dict construction needed.

---

### 3. Chain Composition — LCEL Runnables (langchain-core)

> **File:** `src/services/llm_service.py`, `src/services/rag_chain.py`

The entire pipeline is composed using **LangChain Expression Language (LCEL)** — LangChain's declarative way of building chains with the `|` (pipe) operator.

#### Summarization Chain (LCEL)

```python
from langchain_core.output_parsers import StrOutputParser

# Compose: input → prompt → LLM → parse output to string
summarizer = {"element": lambda x: x} | prompt | _get_text_llm() | StrOutputParser()

# Batch process multiple chunks with concurrency control
text_summaries = summarizer.batch(
    [str(t) for t in texts],
    {"max_concurrency": 3}    # LangChain handles parallel execution
)
```

#### RAG Chain (LCEL)

```python
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

def get_rag_chain(retriever):
    # Step 1: Set up parallel retrieval + question passthrough
    setup_and_retrieval = {
        "context": retriever | RunnableLambda(parse_docs),  # retrieve → split by type
        "question": RunnablePassthrough(),                   # pass question through
    }

    # Step 2: Compose the full chain
    chain = (
        setup_and_retrieval
        | RunnableLambda(build_prompt)    # build multi-modal prompt
        | _get_text_llm()                # send to LLM
        | StrOutputParser()              # extract string response
    )

    # Step 3: Chain variant that also returns source documents
    chain_with_sources = setup_and_retrieval | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt) | _get_text_llm() | StrOutputParser()
        )
    )

    return chain, chain_with_sources
```

**Key LCEL components used:**

| Component | What It Does | Where Used |
|-----------|-------------|------------|
| `RunnablePassthrough()` | Passes input through unchanged | Forwarding the user question alongside retrieval |
| `RunnableLambda(fn)` | Wraps a Python function as a chain step | `parse_docs` (split images/text), `build_prompt` (create multi-modal prompt) |
| `StrOutputParser()` | Extracts string content from LLM response | End of every chain |
| `RunnablePassthrough().assign()` | Passes input through while adding computed fields | `chain_with_sources` — adds `response` field to retrieval output |
| `\|` pipe operator | Connects chain steps sequentially | Entire pipeline composition |
| `.batch()` | Runs chain over multiple inputs with concurrency | Summarizing all text chunks, tables, and images in parallel |

**Why LangChain here?** LCEL lets us compose complex pipelines declaratively. Each step (retrieve → parse → prompt → LLM → parse output) is a composable unit. We get `.batch()` with concurrency control, `.invoke()` for single calls, and `.stream()` for streaming — all for free. Without LangChain, we'd need to manually orchestrate async calls, handle batching, and wire up each step.

---

### 4. Embeddings — `HuggingFaceEmbeddings` (langchain-huggingface)

> **File:** `src/services/vector_service.py`

Document embeddings are generated using LangChain's `HuggingFaceEmbeddings` wrapper around `sentence-transformers`.

```python
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name=settings.embedding_model_name  # "all-MiniLM-L6-v2"
)
```

**Why LangChain here?** `HuggingFaceEmbeddings` implements LangChain's `Embeddings` interface. This means the same embedding object plugs directly into `Chroma`, retrievers, and any other LangChain component that needs embeddings. Swapping to OpenAI embeddings is a one-line change — replace `HuggingFaceEmbeddings` with `OpenAIEmbeddings`.

---

### 5. Vector Store — `Chroma` (langchain-chroma)

> **File:** `src/services/vector_service.py`, `src/services/retrieval_service.py`

ChromaDB is accessed entirely through LangChain's `Chroma` wrapper, not the raw `chromadb` client.

```python
from langchain_chroma import Chroma

vectorstore = Chroma(
    collection_name="document_summaries",
    embedding_function=embeddings,          # HuggingFaceEmbeddings instance
    persist_directory="./chroma_db",
)

# Add documents with metadata
vectorstore.add_documents([
    Document(
        page_content="Summary of the text chunk...",
        metadata={"doc_id": "uuid-here", "type": "text"}
    )
])

# Create a retriever (LangChain abstraction)
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)
```

**Why LangChain here?** `Chroma` wraps the vector store behind LangChain's `VectorStore` interface. The `.as_retriever()` method returns a `VectorStoreRetriever` that plugs directly into LCEL chains. We can swap Chroma for Pinecone, Weaviate, or FAISS by changing one line — the retrieval chain stays identical.

---

### 6. Document Model — `Document` (langchain-core)

> **File:** `src/services/retrieval_service.py`, `src/services/rag_chain.py`

All documents flowing through the pipeline use LangChain's `Document` class — the standard container for text + metadata.

```python
from langchain_core.documents import Document

# Storing summaries in vector store with metadata linking to originals
summary_doc = Document(
    page_content="This table shows quarterly revenue growth...",
    metadata={
        "doc_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "table"    # text | table | image
    }
)
```

**Why LangChain here?** `Document` is LangChain's universal data container. Every retriever, vector store, and chain expects `Document` objects. Using it means our documents flow seamlessly through the entire LangChain ecosystem without any conversion.

---

### 7. Multi-Modal Messages — `HumanMessage` (langchain-core)

> **File:** `src/services/rag_chain.py`

The RAG chain builds multi-modal prompts that include both text context and base64 images, using LangChain's message classes.

```python
from langchain_core.messages import HumanMessage

def build_prompt(kwargs):
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]

    # Build content blocks: text + images
    prompt_content = [
        {"type": "text", "text": f"Context: {context_text}\nQuestion: {user_question}"}
    ]

    # Attach retrieved images as base64
    for image in docs_by_type.get("images", []):
        prompt_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image}"},
        })

    return [HumanMessage(content=prompt_content)]
```

**Why LangChain here?** `HumanMessage` handles multi-modal content blocks natively. The same message format works with any vision-capable LLM (Llava, GPT-4V, Claude) — LangChain handles the provider-specific formatting.

---

### End-to-End Data Flow Through LangChain

```
                     INGESTION PIPELINE
                     ==================

 PDF Document
      │
      ▼
 ┌─────────────┐
 │ Unstructured │ ── partition() + chunk_by_title()
 │   Library    │    Extracts: texts, tables, images
 └──────┬──────┘
        │
        ▼
 ┌──────────────────────────────────┐
 │   LangChain Summarization Chain  │
 │                                  │
 │ Text/Tables:                     │
 │   ChatPromptTemplate             │
 │     | ChatOllama (deepseek-r1)   │
 │     | StrOutputParser            │
 │     .batch(texts, concurrency=3) │
 │                                  │
 │ Images:                          │
 │   ChatPromptTemplate (multimodal)│
 │     | ChatOllama (llava)         │
 │     | StrOutputParser            │
 │     .batch(images, concurrency=3)│
 └──────────┬───────────────────────┘
            │
            ▼
 ┌────────────────────────────────────┐
 │  LangChain Chroma Vector Store     │
 │                                    │
 │  Summaries → HuggingFaceEmbeddings │
 │           → Chroma.add_documents() │
 │                                    │
 │  Originals → SimpleDocStore (JSON) │
 │  (linked by doc_id in metadata)    │
 └────────────────────────────────────┘


                     QUERY PIPELINE
                     ==============

 User Question: "What are the key findings?"
      │
      ▼
 ┌─────────────────────────────────────┐
 │  LangChain LCEL RAG Chain           │
 │                                     │
 │  ┌──────────────────────────────┐   │
 │  │ VectorStoreRetriever         │   │
 │  │  (Chroma.as_retriever)       │   │
 │  │  search_type="similarity"    │   │
 │  │  k=5                         │   │
 │  └──────────┬───────────────────┘   │
 │             │                       │
 │             ▼                       │
 │  ┌──────────────────────────────┐   │
 │  │ RunnableLambda(parse_docs)   │   │
 │  │  Split into: images + texts  │   │
 │  └──────────┬───────────────────┘   │
 │             │                       │
 │             ▼                       │
 │  ┌──────────────────────────────┐   │
 │  │ RunnableLambda(build_prompt)  │   │
 │  │  Multi-modal HumanMessage    │   │
 │  │  with text context + images  │   │
 │  └──────────┬───────────────────┘   │
 │             │                       │
 │             ▼                       │
 │  ┌──────────────────────────────┐   │
 │  │ ChatOllama (deepseek-r1)     │   │
 │  │  Generate answer from context│   │
 │  └──────────┬───────────────────┘   │
 │             │                       │
 │             ▼                       │
 │  ┌──────────────────────────────┐   │
 │  │ StrOutputParser              │   │
 │  │  Extract string response     │   │
 │  └──────────────────────────────┘   │
 └─────────────────────────────────────┘
      │
      ▼
 {"answer": "The key findings are...", "sources": [...]}
```

---

### Summary: LangChain Components at a Glance

| LangChain Component | Package | File(s) | Purpose |
|---------------------|---------|---------|---------|
| `ChatOllama` | `langchain-ollama` | `llm_service.py`, `rag_chain.py` | LLM wrapper for Ollama (Deepseek, Llava) |
| `ChatPromptTemplate` | `langchain-core` | `llm_service.py` | Structured prompt templates with variable injection |
| `StrOutputParser` | `langchain-core` | `llm_service.py`, `rag_chain.py` | Parse LLM output to plain string |
| `RunnableLambda` | `langchain-core` | `rag_chain.py` | Wrap Python functions as chain steps |
| `RunnablePassthrough` | `langchain-core` | `rag_chain.py` | Pass data through unchanged in chains |
| `HumanMessage` | `langchain-core` | `rag_chain.py` | Multi-modal message with text + images |
| `Document` | `langchain-core` | `retrieval_service.py` | Standard text + metadata container |
| `Chroma` | `langchain-chroma` | `vector_service.py` | Vector store for semantic search |
| `VectorStoreRetriever` | `langchain-core` | `retrieval_service.py` | Retriever abstraction from vector store |
| `HuggingFaceEmbeddings` | `langchain-huggingface` | `vector_service.py` | Sentence-transformer embeddings |
| `.batch()` | `langchain-core` | `ingestion_service.py` | Parallel batch execution with concurrency |
| LCEL `\|` pipe | `langchain-core` | `llm_service.py`, `rag_chain.py` | Declarative chain composition |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/files/upload` | Upload a single document |
| `POST` | `/files/upload/multiple` | Batch upload multiple files |
| `POST` | `/files/process/{file_id}` | Trigger document ingestion (async) |
| `GET` | `/files/status/{file_id}` | Check processing status |
| `POST` | `/query/ask` | Ask questions about your documents |
| `DELETE` | `/files/delete?file_id=` | Remove a document |

---

## Getting Started

### Prerequisites

**macOS system dependencies:**
```bash
brew install libmagic poppler tesseract
```

**Ollama (local LLM server):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:8b
ollama pull llava
```

### Installation

```bash
git clone <repo-url>
cd ai-document-companion

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Run the Server

```bash
# Start Ollama first (in a separate terminal)
ollama serve

# Start the API server
uvicorn src.main:app --reload
```

Visit **http://localhost:8000/docs** for interactive Swagger documentation.

---

## Usage Example

```bash
# 1. Upload a document
curl -X POST "http://localhost:8000/files/upload" \
  -F "file=@document.pdf"
# → {"message": "File uploaded successfully", "file_id": "abc123..."}

# 2. Process the document (runs ingestion pipeline in background)
curl -X POST "http://localhost:8000/files/process/abc123"
# → {"status": "processing", "message": "Poll /files/status/abc123 for updates."}

# 3. Check status
curl "http://localhost:8000/files/status/abc123"
# → {"status": "processed"}

# 4. Ask questions
curl -X POST "http://localhost:8000/query/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings in this document?"}'
# → {"answer": "The key findings are...", "sources": [...]}
```

---

## Project Structure

```
src/
├── main.py                  # FastAPI app, exception handlers, logging setup
├── config/
│   ├── environment.py       # Pydantic Settings (env vars)
│   ├── constants.py         # Centralized defaults (search_k, temperatures, etc.)
│   ├── prompts.py           # LLM prompt templates
│   └── file_types.py        # Allowed MIME types
├── core/
│   ├── exceptions.py        # Custom exception hierarchy (AppError → domain errors)
│   └── logger.py            # Structured logging configuration
├── routes/                  # FastAPI route definitions
├── controllers/             # Request handling, delegates to services
├── services/
│   ├── file_service.py      # File upload, storage, deletion
│   ├── process_service.py   # Processing orchestration, status tracking
│   ├── query_service.py     # RAG query entry point
│   ├── ingestion_service.py # Full ingestion pipeline (partition → summarize → store)
│   ├── llm_service.py       # LangChain LLM factories + summarization chains
│   ├── rag_chain.py         # LangChain LCEL RAG chain construction
│   ├── vector_service.py    # ChromaDB + DocStore (via LangChain Chroma)
│   ├── retrieval_service.py # Multi-vector retriever (via LangChain VectorStoreRetriever)
│   ├── chunk_service.py     # Separate text/table/image elements
│   └── unstructured_service.py  # Document partitioning (Unstructured library)
├── models/                  # SQLAlchemy ORM models
└── db/                      # Database engine, session, base mixins
```

---

## Key Design Decisions

- **Local-first**: Uses Ollama for LLM inference — no API keys or cloud dependencies required
- **Multi-modal RAG**: Handles text, tables, and images from documents using vision models
- **Agentic retrieval**: Stores summaries in vector DB, retrieves originals from docstore (multi-vector pattern)
- **LangChain LCEL**: All chains built with the pipe operator — composable, swappable, batchable
- **Provider-agnostic**: Swap `ChatOllama` → `ChatOpenAI` or `Chroma` → `Pinecone` with one-line changes
- **Async processing**: Document ingestion runs in FastAPI background tasks
- **Clean architecture**: Routes → Controllers → Services separation with custom domain exceptions

---

## License

MIT License — see [LICENSE](LICENSE)
