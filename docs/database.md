# Database Layer — A Complete Guide

This document walks you through every database concept used in this project. If you're new to SQLAlchemy 2.0 or FastAPI, this is your starting point.

---

## Table of Contents

- [The Big Picture](#the-big-picture)
- [Engine, Session, and the Connection Pool](#engine-session-and-the-connection-pool)
- [The Database Lifecycle: How Every Request Gets a Session](#the-database-lifecycle-how-every-request-gets-a-session)
- [Base Classes and Mixins: Don't Repeat Yourself](#base-classes-and-mixins-dont-repeat-yourself)
- [Modern SQLAlchemy Syntax: Mapped and mapped_column](#modern-sqlalchemy-syntax-mapped-and-mapped_column)
- [Enums: Python Enums vs Database Enums](#enums-python-enums-vs-database-enums)
- [Relationships: How Models Talk to Each Other](#relationships-how-models-talk-to-each-other)
- [Soft Deletion vs Hard Deletion](#soft-deletion-vs-hard-deletion)
- [Table Creation: How init_db Works](#table-creation-how-init_db-works)
- [SQLite Quirks in This Project](#sqlite-quirks-in-this-project)
- [Model Reference](#model-reference)

---

## The Big Picture

Think of the database layer as a three-tier stack:

```
Your FastAPI Route
       |
       |  "I need to save a user"
       v
  SQLAlchemy ORM  (Python objects <-> SQL rows)
       |
       |  "INSERT INTO users ..."
       v
  Database Engine  (SQLite in dev, PostgreSQL in prod)
```

You never write raw SQL. Instead, you work with Python objects (`User`, `Document`, etc.), and SQLAlchemy translates your Python operations into SQL behind the scenes.

---

## Engine, Session, and the Connection Pool

These three concepts are the foundation. Here's a real-world analogy:

| Concept | Analogy | What It Does |
|---------|---------|-------------|
| **Engine** | The database's phone line | A single, long-lived object that knows *how* to connect to your database. Created once at startup. |
| **Connection Pool** | A set of open phone lines | Instead of dialing (connecting) every time, the engine keeps a few lines open and reuses them. Much faster. |
| **Session** | A single phone call | A short-lived conversation with the database. You open one, do your work (queries, inserts), and hang up. |

Here's how we create them in `src/db/session.py`:

```python
# The engine — created ONCE when the app starts
engine = create_db_engine()

# The session factory — a "template" for creating sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Why `autocommit=False`?** Because we want explicit control. Nothing is saved to the database until you call `db.commit()`. This means if something goes wrong halfway through, nothing partial gets saved — your data stays consistent.

**Why `autoflush=False`?** By default, SQLAlchemy would send pending changes to the database before every query (a "flush"). Turning this off gives us more predictable behavior — changes only go to the database when we explicitly commit.

### Connection Pool: SQLite vs PostgreSQL

The engine is configured differently depending on the database:

```python
# SQLite (development)
engine = create_engine( # A long lived object that knows how to connect db.
    url,
    connect_args={"check_same_thread": False},  # Allow FastAPI threads to share connection
    poolclass=StaticPool,                         # One shared connection (SQLite limitation)
)

# PostgreSQL (production)
engine = create_engine(
    url,
    pool_size=20,       # Keep 20 connections open and ready
    max_overflow=40,    # Allow up to 40 extra connections during traffic spikes
    pool_pre_ping=True, # Test each connection before using it (handles stale connections)
)
```

**`pool_pre_ping=True`** is like checking if the phone line is still active before speaking. If a connection went stale (maybe the database restarted), SQLAlchemy silently replaces it instead of crashing your request.

---

## The Database Lifecycle: How Every Request Gets a Session

This is one of the most important patterns in the project. Every HTTP request needs its own database session, and that session **must** be closed when the request ends — even if the request crashes.

Here's the code in `src/dependencies/db.py`:

```python
from collections.abc import Iterator
from sqlalchemy.orm import Session
from src.db.session import SessionLocal

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Let's break this down piece by piece.

### What `yield` Does Here

This function is a **generator** — that `yield` keyword is the giveaway. Instead of returning a value and finishing, it *pauses* at `yield`, hands the session to your route, and then *resumes* after your route finishes (to run the `finally` block).

Think of it like a librarian:

1. **Before yield:** The librarian checks out a book (opens a session).
2. **At yield:** You take the book and read it (your route does queries).
3. **After yield (finally):** The librarian takes the book back and re-shelves it (closes the session) — no matter what happened.

### Why `try/finally`?

The `finally` block runs **no matter what** — even if your route throws an exception. Without it, a crashing request would leak a database connection. Over time, you'd run out of connections and the whole app would freeze. The `finally` block is your safety net.

### The Type Hint Mystery: `Iterator[Session]` vs `Session`

This confuses a lot of people. The function signature says it returns `Iterator[Session]`, but your route receives a plain `Session`:

```python
# The dependency says Iterator[Session]
def get_db() -> Iterator[Session]:
    ...
    yield db  # yields a Session

# But the route receives just Session
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # db is a Session, not an Iterator!
```

**Why?** FastAPI is smart about generators. When it sees a generator dependency (a function with `yield`), it:
1. Calls `next()` on the generator to get the yielded value → that's your `Session`
2. Injects that `Session` into your route parameter
3. After your route finishes, calls `next()` again to trigger the `finally` block

So the *function* returns an Iterator (because it's a generator), but FastAPI *unwraps* it and gives your route the actual Session inside. The type hint `Iterator[Session]` is technically correct for Python, while your route's `db: Session` is what you actually work with.

---

## Base Classes and Mixins: Don't Repeat Yourself

Every model in this project needs an ID, a created timestamp, and an updated timestamp. Instead of copy-pasting those columns into every model, we use **mixins** — reusable building blocks.

All of this lives in `src/db/base.py`.

### DeclarativeBase: The Foundation

```python
class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass
```

Every model inherits from `Base`. This is how SQLAlchemy knows "this Python class represents a database table." It also collects all your models into a registry so `Base.metadata.create_all()` can create all tables at once.

### UUIDMixin: Universal IDs

```python
class UUIDMixin:
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
```

**Why UUIDs instead of auto-incrementing integers?**
- **No collisions:** You can generate IDs in Python *before* inserting into the database. Two servers will never generate the same ID.
- **No information leakage:** Sequential IDs (`/users/1`, `/users/2`) let anyone guess how many users you have. UUIDs reveal nothing.
- **Merge-friendly:** If you ever need to merge data from two databases, UUIDs won't clash.

**Why `default=lambda: str(uuid.uuid4())`?** The `lambda` is important. Without it, `uuid.uuid4()` would be called once when the class loads, and every row would get the *same* ID. The lambda ensures a fresh UUID is generated for each new row.

### TimestampMixin: Automatic Timestamps

```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,       # Python-side default
        server_default=func.now(),      # Database-side default
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,      # Auto-updates on every change
        server_default=func.now(),
        nullable=False,
    )
```

Two things to notice:

1. **`default` vs `server_default`:** `default` runs in Python (SQLAlchemy generates the timestamp before sending the INSERT). `server_default` runs in the database (the SQL itself contains `DEFAULT NOW()`). Having both means timestamps work whether you insert via the ORM or via raw SQL/migrations.

2. **`onupdate=datetime.utcnow`:** This is magic for `updated_at`. Every time you modify a row and commit, SQLAlchemy automatically refreshes this timestamp. You never have to remember to set it manually.

### SoftDeleteMixin: Mark as Deleted Without Losing Data

```python
class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

This mixin is available but not currently used by any model — it's there for future use. See the [Soft Deletion section](#soft-deletion-vs-hard-deletion) below for why it exists.

### How a Model Uses Mixins

Here's how the `User` model combines everything:

```python
class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    ...
```

Python's multiple inheritance means `User` gets all columns from `Base`, `UUIDMixin`, and `TimestampMixin` — plus its own `email`, `hashed_password`, etc. The final table has columns from all three parents plus its own.

---

## Modern SQLAlchemy Syntax: Mapped and mapped_column

If you've seen older SQLAlchemy code, it looks like this:

```python
# OLD style (SQLAlchemy 1.x)
email = Column(String(255), unique=True, nullable=False)
```

This project uses the **modern 2.0 style**:

```python
# NEW style (SQLAlchemy 2.0)
email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
```

### Why Two Things? `Mapped[str]` and `mapped_column(String(255))`

They serve different audiences:

| Part | Audience | Purpose |
|------|----------|---------|
| `Mapped[str]` | **Python** and your IDE | "This attribute is a string." Your editor gives you autocomplete, and type checkers (mypy/pyright) catch bugs like `user.email + 123`. |
| `mapped_column(String(255))` | **The database** | "This column is VARCHAR(255)." This is what actually gets written into the CREATE TABLE SQL. |

Think of it this way: `Mapped[str]` is the **promise** ("this will be a string"), and `mapped_column(String(255))` is the **implementation** ("specifically, a 255-character varchar in the database").

### Optional Fields

```python
# Required — Python: str, Database: NOT NULL
email: Mapped[str] = mapped_column(String(255), nullable=False)

# Optional — Python: str | None, Database: NULL allowed
full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
```

When you write `Mapped[Optional[str]]`, you're telling Python "this might be `None`." When you write `nullable=True`, you're telling the database "this column allows NULL." They work together — the Python type hint and the database constraint should always agree.

### Column Alias: When Python Names Clash with SQL

Look at this from the `Conversation` model:

```python
conversation_metadata: Mapped[Optional[dict]] = mapped_column(
    "metadata", JSON, nullable=True, default=dict,
)
```

The first argument `"metadata"` is the **database column name**. The Python attribute is `conversation_metadata`. Why? Because `metadata` is a reserved name in SQLAlchemy (it refers to the schema metadata). So we give Python a safe name while keeping the database column clean.

---

## Enums: Python Enums vs Database Enums

The project uses Python enums extensively:

```python
class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"
```

Notice `(str, Enum)` — this makes each member both a string and an enum value. That means `DocumentStatus.UPLOADED == "uploaded"` is `True`, which makes comparisons and JSON serialization seamless.

In the model, it maps to a database column:

```python
status: Mapped[DocumentStatus] = mapped_column(
    SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False, index=True,
)
```

**In Python:** You work with `document.status = DocumentStatus.PROCESSING` — type-safe, with autocomplete.

**In the database:** The column stores the string `"processing"`. SQLAlchemy handles the conversion both ways.

**Why `index=True` on status?** Because you'll often query "give me all documents that are processing." An index makes that query fast even with thousands of documents.

---

## Relationships: How Models Talk to Each Other

### One-to-Many: Document → Chunks

A document has many chunks. This is expressed from both sides:

```python
# In Document model
chunks: Mapped[List["Chunk"]] = relationship(
    "Chunk", back_populates="document", cascade="all, delete-orphan", lazy="dynamic",
)

# In Chunk model
document_id: Mapped[str] = mapped_column(
    String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True,
)
document: Mapped["Document"] = relationship("Document", back_populates="chunks")
```

Let's unpack the key arguments:

**`back_populates`** links the two sides. When you access `document.chunks`, SQLAlchemy knows to look at the `Chunk` model's `document` attribute, and vice versa. They stay in sync.

**`cascade="all, delete-orphan"`** means: if you delete a Document in Python (`db.delete(document)`), SQLAlchemy also deletes all its Chunks automatically. "delete-orphan" goes further — if you remove a chunk from `document.chunks`, that chunk gets deleted too (it can't exist without a parent).

**`ondelete="CASCADE"` on the ForeignKey** is the *database-level* equivalent. If a row is deleted directly in SQL (bypassing the ORM), the database itself will cascade the delete. Belt and suspenders.

**`lazy="dynamic"`** means `document.chunks` doesn't load all chunks into memory immediately. Instead, it returns a query object that you can filter, paginate, or iterate over. Crucial when a document might have thousands of chunks.

### **ORM relationships**
* What you define with `relationship()` is **not stored in the database**.
* It’s purely **Python-side**, a convenience object to access related rows.

```python id="0z4c7r"
document: Mapped["Document"] = relationship("Document", back_populates="chunks")
```
- Not stored in the database
- Returns a **Python `Document` object**
- Uses the foreign key (`document_id`) to fetch the document when needed

---

### Why `TYPE_CHECKING` Guards?

You'll see this pattern in every model:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.chunk import Chunk
```

This avoids **circular imports**. Document imports Chunk, and Chunk imports Document — that would crash Python. The `TYPE_CHECKING` flag is `True` only when a type checker (mypy) analyzes the code, and `False` at runtime. So the import only exists for autocomplete and type checking, not when the app actually runs.

The `relationship("Chunk")` uses a **string** instead of the class directly, so SQLAlchemy resolves it lazily at runtime after all models are loaded.

---

## Soft Deletion vs Hard Deletion

There are two strategies used in this project:

### Hard Deletion (Chunks, Messages)

```python
# ForeignKey with CASCADE — when the parent is deleted, children are destroyed
ForeignKey("documents.id", ondelete="CASCADE")
```

The row is permanently removed from the database. Gone forever. Used for chunks and messages because they have no value without their parent.

### Soft Deletion via Flag (Conversations)

```python
# In Conversation model
is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

def deactivate(self) -> None:
    self.is_active = False
```

The row stays in the database, but `is_active` is set to `False`. Every query filters on `is_active=True`, so "deleted" conversations are invisible to the app but recoverable by an admin.

**When to use which?**

| Strategy | Use When | Example |
|----------|----------|---------|
| **Hard delete** | Data has no standalone value; keeping it wastes space | Chunks of a deleted document |
| **Soft delete (flag)** | You might need to undo, audit, or recover | Conversations (user might want them back) |
| **Soft delete (timestamp)** | Same as above, but you also want to know *when* | The `SoftDeleteMixin` with `deleted_at` (available, not yet in use) |

### SoftDeleteMixin (Available for Future Use)

The `SoftDeleteMixin` in `src/db/base.py` provides a `deleted_at` timestamp approach. Instead of a boolean flag, it records the exact moment something was deleted, which is useful for audit trails and time-based cleanup jobs. No model currently uses it, but it's ready when needed.

---

## Table Creation: How init_db Works

```python
def init_db() -> None:
    """Create all database tables."""
    from src.models import document, conversation, message, chunk, user  # noqa: F401
    Base.metadata.create_all(bind=engine)
```

This runs at application startup (`@app.on_event("startup")`).

**Why the imports?** SQLAlchemy's `Base.metadata` only knows about models that have been *imported* into Python's memory. If you skip the `Chunk` import, the `chunks` table won't be created. These imports ensure every model is registered before `create_all()` runs.

**What does `create_all()` do?** It checks each model's table against the database. If the table doesn't exist, it creates it. If it already exists, it does nothing (it will **not** alter existing tables — that's what migration tools like Alembic are for).

---

## SQLite Quirks in This Project

SQLite has some behaviors that differ from PostgreSQL. The project handles two of them:

### 1. Foreign Keys Are Off by Default

```python
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

Surprisingly, SQLite ignores foreign key constraints unless you explicitly turn them on for each connection. Without this, you could delete a `Document` and its `Chunk` rows would be left orphaned — the `CASCADE` wouldn't fire. This event listener runs `PRAGMA foreign_keys=ON` on every new connection.

### 2. Thread Safety

```python
connect_args={"check_same_thread": False}
```

SQLite's default Python driver refuses to let a connection be used from a different thread than the one that created it. FastAPI uses multiple threads, so we disable this check. Combined with `StaticPool` (a single shared connection), this lets FastAPI's thread pool share the SQLite connection safely.

---

## Model Reference

A quick overview of every model and its purpose:

### User (`src/models/user.py`)

| Column | Type | Why It's Needed |
|--------|------|----------------|
| `id` | UUID (string) | From UUIDMixin. Primary key — referenced by `documents.user_id` and `conversations.user_id` to scope all data per user. |
| `email` | String(255) | The login identifier. **Unique** so no two accounts share an email. **Indexed** because every login query filters by email. |
| `hashed_password` | String(255) | Stores the bcrypt hash — never the plain-text password. The app calls `bcrypt.checkpw()` to compare during login without ever decrypting. |
| `full_name` | String(255) | **Optional** display name for the UI. Separate from `email` because not every user wants to share their real name, and emails aren't user-friendly to display. |
| `is_active` | Boolean | A soft-disable switch. Set to `False` to lock an account without deleting it. The auth dependency checks this on every request — a deactivated user gets 403 even with a valid JWT. |
| `created_at` | DateTime | From TimestampMixin. Tracks when the user registered — useful for admin dashboards and user analytics. |
| `updated_at` | DateTime | From TimestampMixin. Auto-updates on any row change — lets you know when the profile or active status was last modified. |

### Document (`src/models/document.py`)

| Column | Type | Why It's Needed |
|--------|------|----------------|
| `id` | UUID (string) | From UUIDMixin. Used everywhere — in URLs (`/process/{file_id}`), status files, vector store metadata, and chunk foreign keys. |
| `user_id` | String(36) | Ties the document to its owner. **Optional** because the file upload flow creates the file on disk first (via `FileService`) before a DB row may exist. **Indexed** because every query filters by user. |
| `filename` | String(255) | The **original name** the user uploaded (e.g., `"Q3-report.pdf"`). Needed to display in the UI. **Indexed** for search/filtering. |
| `content_type` | String(100) | Raw MIME type from the upload (e.g., `"application/pdf"`). Preserved separately from `doc_type` because it's the exact value the browser sent — useful for content negotiation and re-downloads. |
| `doc_type` | Enum | A **simplified enum** (`PDF`, `DOCX`, `TXT`, etc.) derived from `content_type`. Exists because you don't want to compare against `"application/vnd.openxmlformats-officedocument.wordprocessingml.document"` everywhere — `doc_type == DocumentType.DOCX` is cleaner for conditionals, filtering, and analytics. |
| `file_path` | String(500) | Absolute/relative path to the file on disk. **Optional** because the file could be deleted from disk while the metadata row persists (status = `DELETED`). |
| `file_size` | Integer | Size in bytes. Used for upload quota enforcement, UI display ("3.2 MB"), and monitoring storage usage — without hitting the filesystem. |
| `page_count` | Integer | Set **after** processing — the ingestion pipeline discovers this during parsing. **Optional** because it's unknown at upload time and not all formats have "pages" (CSV, JSON). |
| `chunk_count` | Integer | How many chunks the document was split into. Useful for debugging ("why did my 2-page PDF produce 47 chunks?") and for the UI to show processing results. Defaults to `0`. |
| `status` | Enum | **The most important field.** Tracks the document's lifecycle: `UPLOADED → PROCESSING → PROCESSED` (or `FAILED` / `DELETED`). **Indexed** because the app constantly queries "give me all documents that are processing" or "all processed documents for this user." |
| `error_message` | Text | When `status = FAILED`, this stores **why** (e.g., `"Unsupported image format in page 3"`). **Optional** — only populated on failure. Cleared by `mark_processing()` and `mark_processed()` so a retry doesn't show a stale error. |
| `processed_at` | DateTime | Timestamp of when processing completed. Separate from `updated_at` because `updated_at` changes on *any* modification (status change, metadata update), but `processed_at` specifically answers "when was the RAG pipeline finished?" |

**Relationships:** `chunks` → one-to-many with Chunk (cascade delete)

**Helper methods:** `mark_processing()`, `mark_processed()`, `mark_failed()` — these encapsulate status transitions so you don't scatter status logic across services.

**The two enums:**

`DocumentStatus` is a state machine:
```
UPLOADED → PROCESSING → PROCESSED
              ↓
            FAILED
              ↓
          (retry) → PROCESSING → ...

Any state → DELETED
```

`DocumentType` exists because the same logical format can have multiple MIME types (e.g., `.doc` is `application/msword`, `.docx` is the long OpenXML string). The enum normalizes these into a single clean value for filtering and display.

### Chunk (`src/models/chunk.py`)

| Column | Type | Why It's Needed |
|--------|------|----------------|
| `id` | UUID (string) | From UUIDMixin. Used as the key in the SQLite docstore to retrieve original content during RAG queries. |
| `document_id` | FK → documents.id | Links this chunk back to its parent document. **CASCADE delete** — when a document is deleted, all its chunks are automatically destroyed. **Indexed** because retrieval queries filter by document. |
| `chunk_type` | Enum | Classifies the content: `TEXT`, `TABLE`, `IMAGE`, `CODE`, `HEADING`. The RAG pipeline processes each type differently — text and tables get text-based summarization, images get vision-model summarization. Also used to tag vector store metadata so retrieval can filter by content type. |
| `page_number` | Integer | Which page of the source document this chunk came from. **Optional** because not all formats have pages (plain text, CSV). Used to cite sources in RAG answers ("see page 7"). |
| `position` | Integer | The chunk's order within the document (0, 1, 2, ...). Ensures chunks can be reconstructed in reading order — important because vector similarity search returns results in relevance order, not document order. |
| `char_count` | Integer | Number of characters in the chunk. Useful for debugging chunking quality (are chunks too small? too large?) and for estimating token counts before sending to the LLM. |
| `summary` | Text | The LLM-generated summary of this chunk. This is what gets **embedded** into ChromaDB's vector space. Stored here so you can inspect/debug what the LLM produced without querying the vector store. |
| `vector_id` | String(36) | The ID of this chunk's embedding in ChromaDB. Links the relational world (SQLAlchemy) to the vector world (Chroma). **Indexed** for fast lookups when translating vector search results back to chunk metadata. |

**Relationships:** `document` → belongs to Document

**The `effective_vector_id` property:** Falls back to the chunk's own `id` if no separate `vector_id` was assigned. This means chunks always have a usable vector reference, even if the vector store insertion hasn't happened yet.

### Conversation (`src/models/conversation.py`)

| Column | Type | Why It's Needed |
|--------|------|----------------|
| `id` | UUID (string) | From UUIDMixin. Used in URLs (`/conversations/{id}/ask`) and as the foreign key for messages. |
| `title` | String(255) | A human-readable label for the conversation list UI. **Optional** at creation — auto-set from the first user message via `set_title_from_first_message()` (truncated to 50 chars). Without this, the UI would show a list of meaningless UUIDs. |
| `user_id` | String(36) | Scopes the conversation to its owner. **Every query** filters on this — user A can never see user B's conversations. **Indexed** because listing conversations is a frequent operation. |
| `document_ids` | JSON | A list of document UUIDs that provide context for this conversation. Stored as JSON (not a join table) because it's a lightweight reference — the app doesn't need to query "all conversations for document X." It's append-only via `add_document_context()`. |
| `is_active` | Boolean | **Soft delete flag.** `DELETE /conversations/{id}` sets this to `False` instead of destroying the row. All queries filter `is_active=True`, so deleted conversations are invisible but recoverable. **Indexed** because it's in every WHERE clause. |
| `last_message_at` | DateTime | Tracks when the most recent message was added. Used for sorting conversations by "most recently active" — cheaper than joining the messages table and finding `MAX(created_at)` on every list request. |
| `message_count` | Integer | A running counter incremented by `update_last_message()`. Displayed in the conversation list UI ("12 messages") without needing a `COUNT(*)` query on the messages table. A denormalized optimization. |
| `metadata` (aliased as `conversation_metadata`) | JSON | A flexible key-value bag for future use — things like conversation settings, model preferences, or tags. Aliased in Python because `metadata` is a reserved SQLAlchemy name. |

**Relationships:** `messages` → one-to-many with Message (cascade delete, ordered by `created_at`, dynamic loading)

**Why `last_message_at` and `message_count` are denormalized:** Both could be computed from the messages table (`MAX(created_at)` and `COUNT(*)`), but the conversation list endpoint is called frequently. Storing these on the conversation row avoids an expensive join/aggregation on every list request. The trade-off is that `add_message()` must always call `update_last_message()` to keep them in sync.

### Message (`src/models/message.py`)

| Column | Type | Why It's Needed |
|--------|------|----------------|
| `id` | UUID (string) | From UUIDMixin. Uniquely identifies each message — needed if the UI supports editing, deleting, or linking to specific messages. |
| `conversation_id` | FK → conversations.id | Links this message to its conversation. **CASCADE delete** — if a conversation is hard-deleted, all messages go with it. **Indexed** because every message query filters by conversation. |
| `role` | Enum | Who sent the message: `USER`, `ASSISTANT`, or `SYSTEM`. Essential for reconstructing chat history in the correct format for the LLM prompt (the model needs to know which messages are "its" responses vs user questions). |
| `content` | Text | The actual message body. Uses `Text` (unlimited length) instead of `String(N)` because LLM responses can be very long — a detailed answer with code blocks and explanations can easily exceed any fixed limit. |
| `token_count` | Integer | **Optional** — how many LLM tokens this message consumed. Useful for usage tracking, cost monitoring, and enforcing per-user token budgets. Not always set because token counting adds overhead. |
| `sources` | JSON | A list of source references attached to **assistant messages only**. Each entry contains the document ID, chunk type, summary, and original content that the RAG chain used to generate the answer. This is a per-message audit trail — the user can see exactly which documents informed each response. |
| `metadata` (aliased as `message_metadata`) | JSON | A flexible bag for future use — things like feedback ratings ("thumbs up/down"), processing latency, or model version used. Aliased in Python because `metadata` is reserved in SQLAlchemy. |

**Relationships:** `conversation` → belongs to Conversation

**Why `sources` is JSON, not a join table:** Sources are write-once, read-with-message data. You never query "find all messages that cited document X" — you always load a message and display its sources alongside it. A JSON column avoids an extra table and extra joins for this read-heavy, write-once pattern.

**The helper properties:** `is_user` and `is_assistant` are convenience booleans for cleaner conditionals — `if message.is_user:` reads better than `if message.role == MessageRole.USER:`.
