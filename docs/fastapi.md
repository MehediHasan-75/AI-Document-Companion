# FastAPI Layer — A Complete Guide

This document explains every FastAPI concept used in this project. If you're new to FastAPI or coming from Flask/Django, start here.

---

## Table of Contents

- [The Big Picture](#the-big-picture)
- [Application Factory: How the App Boots Up](#application-factory-how-the-app-boots-up)
- [Middleware: The Request Onion](#middleware-the-request-onion)
- [Routing: How URLs Map to Code](#routing-how-urls-map-to-code)
- [Dependency Injection: FastAPI's Superpower](#dependency-injection-fastapis-superpower)
- [Pydantic Schemas: Validating Everything Automatically](#pydantic-schemas-validating-everything-automatically)
- [The Layered Architecture: Routes and Services](#the-layered-architecture-routes-and-services)
- [File Uploads: Handling Binary Data](#file-uploads-handling-binary-data)
- [Background Tasks: Fire-and-Forget Work](#background-tasks-fire-and-forget-work)
- [Exception Handling: One Pattern for All Errors](#exception-handling-one-pattern-for-all-errors)
- [Lifecycle Events: Startup and Shutdown](#lifecycle-events-startup-and-shutdown)
- [Async vs Sync: When It Matters](#async-vs-sync-when-it-matters)
- [API Documentation: Free Swagger UI](#api-documentation-free-swagger-ui)
- [Endpoint Reference](#endpoint-reference)

---

## The Big Picture

When an HTTP request hits this application, it flows through several layers before a response goes back:

```
Client Request
     |
     v
  Middleware Stack         (logging, compression, CORS)
     |
     v
  Route                   (URL matching, parameter extraction)
     |
     v
  Dependency Injection     (auth check, DB session)
     |
     v
  Service                  (business logic, database queries)
     |
     v
  Response back to client
```

Each layer has a clear job. No layer does another layer's work.

---

## Application Factory: How the App Boots Up

Everything starts in `src/main.py`:

```python
app = FastAPI(
    title="AI Document Companion API",
    version="1.0.0",
    description="API for managing files",
)
```

This single line creates the entire application. The `title`, `version`, and `description` aren't just labels — they show up in the auto-generated Swagger UI at `/docs`. If you change them, the documentation updates automatically.

Before any request handling, there's a setup sequence:

```python
setup_logging()           # 1. Configure logging format and levels
# middleware registration  # 2. Add middleware (see next section)
# exception handlers       # 3. Register error handlers
app.include_router(...)   # 4. Attach all routes
# startup event            # 5. init_db() runs when the server starts
```

The order matters. Middleware must be registered before routes are attached, and the startup event fires after everything is wired up.

---

## Middleware: The Request Onion

Middleware wraps around your routes like layers of an onion. Every request passes through each layer on the way in, and every response passes through on the way out — in reverse order.

```
Request →  log_requests → GZip → CORS → Route Handler
Response ← log_requests ← GZip ← CORS ← Route Handler
```

### Registration Order Matters

In FastAPI (and Starlette under the hood), **the last middleware added is the outermost layer**. Our code registers them in this order:

```python
# Added first → innermost (closest to the route)
app.add_middleware(CORSMiddleware, ...)

# Added second → middle
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Added third (via decorator) → outermost (first to touch the request)
@app.middleware("http")
async def log_requests(request, call_next): ...
```

This means `log_requests` runs first on every request and last on every response — so it can accurately measure the total time including middleware processing.

### The Three Middleware Layers

#### 1. Request Logger (outermost)

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d  (%.1f ms)",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response
```

This is a **custom HTTP middleware** — the `@app.middleware("http")` decorator tells FastAPI to run this function on every request. The pattern is always the same:

1. Do something before (`start = time.perf_counter()`)
2. Call `await call_next(request)` to pass the request to the next layer
3. Do something after (log the result)
4. Return the response

**Why `time.perf_counter()` instead of `time.time()`?** `perf_counter` is monotonic (it never jumps backwards due to clock corrections) and has nanosecond resolution. Perfect for measuring durations.

#### 2. GZip Compression (middle)

```python
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

Automatically compresses responses larger than 1000 bytes. The client sends `Accept-Encoding: gzip` in its headers, and this middleware handles the rest. Smaller responses aren't compressed because the overhead isn't worth it.

#### 3. CORS (innermost)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**CORS (Cross-Origin Resource Sharing)** controls which websites can call your API from a browser. Without it, a React app on `localhost:3000` can't make requests to your API on `localhost:8000` — the browser blocks it.

| Setting | What It Does |
|---------|-------------|
| `allow_origins` | Which domains can call the API (loaded from `.env`) |
| `allow_credentials=True` | Allow cookies and `Authorization` headers |
| `allow_methods=["*"]` | Allow all HTTP methods (GET, POST, DELETE, etc.) |
| `allow_headers=["*"]` | Allow all request headers |

**Important for production:** The default `CORS_ALLOWED_ORIGINS` is `["*"]` (any website). In production, restrict this to your actual frontend domain.

### How `call_next` Works Under the Hood

The `call_next(request)` function is the core mechanism of FastAPI middleware. Understanding it is key to understanding the entire middleware system.

```python
@app.middleware("http")
async def my_middleware(request: Request, call_next):
    # 1. Code here runs BEFORE the route handler
    print("Before")

    response = await call_next(request)  # 2. Hand off to route, PAUSE here

    # 3. Code here runs AFTER the route handler
    print("After")
    return response  # 4. Send response back to client
```

**What `await call_next(request)` actually does:**

1. Tells FastAPI: "execute the route handler (and any inner middleware) for this request"
2. The `await` **suspends this middleware coroutine** — it does NOT block the server
3. While this request waits, the **event loop handles other requests freely**
4. Once the route finishes, `call_next` returns the `Response` object
5. Middleware resumes, can inspect/modify the response, then returns it

Think of it like a receptionist: they hand a package to an employee and wait, but while waiting they can receive packages from other clients. Only *this specific request's* middleware is paused — the server keeps serving everyone else.

**Visual flow of a single request:**

```
Request arrives
  → Middleware starts (code before call_next)
  → await call_next(request)  ── pauses middleware, runs route ──┐
                                                                   │
  ← Response comes back  ←────────────────────────────────────────┘
  → Middleware resumes (code after call_next)
  → return response → sent to client
```

### Why There's No `response` Parameter (Express vs FastAPI)

If you're coming from Node.js/Express, you might wonder why FastAPI middleware only receives `request` and `call_next` — no `response` object upfront.

| | Express (Node.js) | FastAPI (Python) |
|--|------------------|-----------------|
| **Middleware signature** | `(req, res, next)` | `(request, call_next)` |
| **Response object** | Pre-created, passed in | Generated by route, returned from `call_next` |
| **How you modify it** | Mutate `res` directly | Modify the returned response object |
| **How you continue** | `next()` | `await call_next(request)` |

The reason: FastAPI follows the **ASGI spec**, where the response doesn't exist until the route handler creates it. The middleware can't receive something that hasn't been created yet. You get the response *from* `call_next()`, then modify it:

```python
response = await call_next(request)
response.headers["X-Request-Time"] = str(duration_ms)
return response
```

### Sync vs Async Middleware

| Type | Declaration | Runs On | Can `await`? | Use For |
|------|------------|---------|-------------|---------|
| **Async** | `async def middleware(request, call_next)` | Event loop | Yes | I/O-bound work (DB checks, HTTP calls, Redis) |
| **Sync** | `def middleware(request, call_next)` | Thread pool | No | CPU-bound or quick operations (logging, headers) |

This project uses `async def` for the request logger because it calls `await call_next(request)`. If your middleware doesn't need `await`, a sync `def` works fine — FastAPI runs it in a thread pool automatically.

**Key rule:** Async middleware that calls blocking (sync) code will freeze the event loop. Either use `async def` with only async operations, or use plain `def` and let FastAPI handle threading.

---

## Routing: How URLs Map to Code

### The Router Hierarchy

Instead of defining all routes on the `app` object directly, this project uses a hierarchy of routers:

```
app (src/main.py)
 └── index.router (src/routes/index.py)       ← master aggregator
      ├── auth_routes.router      prefix="/auth"
      ├── file_routes.router      prefix="/files"
      ├── process_routes.router   prefix="/files"
      ├── query_routes.router     prefix="/query"
      └── conversation_routes.router  prefix="/conversations"
```

Each feature gets its own `APIRouter` with its own prefix and tag:

```python
# src/routes/auth_routes.py
router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", ...)
def register(...): ...
# This endpoint lives at POST /auth/register
```

**The `prefix`** automatically prepends to every route in that file. So `@router.post("/register")` becomes `/auth/register` without repeating `/auth` everywhere.

**The `tags`** group endpoints in the Swagger UI. All auth endpoints appear under the "Auth" heading, file endpoints under "Files," etc.

The index router (`src/routes/index.py`) simply collects them all:

```python
router = APIRouter()
router.include_router(auth_routes.router)
router.include_router(file_routes.router)
# ... etc
```

Then `src/main.py` mounts this single aggregated router:

```python
app.include_router(index.router)
```

**Why this pattern?** Imagine having 50 endpoints all in one file. The router hierarchy keeps each feature in its own module, makes testing easier (you can test routers in isolation), and prevents merge conflicts when multiple people work on different features.

### Path Parameters

```python
@router.post("/process/{file_id}")
async def process_file(file_id: str, ...):
```

The `{file_id}` in the URL path becomes a function parameter. FastAPI matches `/process/abc-123` and passes `"abc-123"` as `file_id`. The type hint `str` tells FastAPI to keep it as a string (if you wrote `file_id: int`, it would auto-convert and return 422 if the value isn't numeric).

### Query Parameters

```python
@router.delete("/delete")
async def delete_file(file_id: str, ...):
```

When a parameter isn't in the path and isn't a Pydantic model, FastAPI treats it as a **query parameter**. This endpoint expects `DELETE /files/delete?file_id=abc-123`.

### Request Body (JSON)

```python
@router.post("/register", ...)
def register(payload: RegisterRequest, ...):
```

When a parameter has a Pydantic model type, FastAPI reads the request body as JSON, validates it against the schema, and gives you a typed Python object. If validation fails, the client gets a 422 response with details about what went wrong — you don't write any of that error handling yourself.

---

## Dependency Injection: FastAPI's Superpower

Dependency injection (DI) is the pattern that makes this project clean. Instead of each route function manually creating database sessions and checking auth tokens, you **declare what you need** and FastAPI provides it.

### How `Depends()` Works

```python
@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    # current_user is already a validated, authenticated User object
    return UserResponse(...)
```

Here's what happens behind the scenes:

1. FastAPI sees `Depends(get_current_user)` in the function signature
2. Before calling `me()`, it calls `get_current_user()` first
3. `get_current_user` itself has dependencies — it needs a token and a DB session
4. FastAPI resolves the **entire dependency tree** automatically:

```
me()
 └── get_current_user()
      ├── oauth2_scheme()        → extracts Bearer token from header
      └── get_db()               → opens a database session
```

### Dependency Chains

The auth dependency is a great example of chaining:

```python
# src/dependencies/auth.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),    # Step 1: extract token
    db: Session = Depends(get_db),          # Step 2: get DB session
) -> User:
    payload = decode_token(token)           # Step 3: verify JWT
    user_id = payload.get("sub")
    return auth_service.get_by_id(db, user_id)  # Step 4: load user
```

**`OAuth2PasswordBearer`** is a FastAPI-provided dependency. It looks for the `Authorization: Bearer <token>` header, extracts the token string, and returns it. If the header is missing, it returns 401 automatically — before your code even runs.

**The `tokenUrl="/auth/login"`** parameter doesn't enforce anything at runtime. It tells Swagger UI where the login endpoint is, so the "Authorize" button knows which URL to call.

### Why Dependencies Beat Manual Code

Without DI, every protected route would look like this:

```python
# WITHOUT dependency injection (bad)
@router.get("/me")
def me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401)
    payload = decode_token(token)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == payload["sub"]).first()
        if not user:
            raise HTTPException(401)
        return UserResponse(...)
    finally:
        db.close()
```

With DI, the same route is:

```python
# WITH dependency injection (good)
@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(...)
```

The auth logic and session management are written **once** and reused everywhere. If the auth logic changes (say, you add role-based access), you update one function.

---

## Pydantic Schemas: Validating Everything Automatically

Pydantic models serve as contracts between the client and the API. They're defined in `src/schemas/`.

### Request Validation

```python
# src/schemas/auth.py
class RegisterRequest(BaseModel):
    email: EmailStr                                    # Must be a valid email
    password: str = Field(..., min_length=8, max_length=128)  # 8-128 chars
    full_name: Optional[str] = None                    # Optional, defaults to None
```

When a client sends `POST /auth/register` with JSON:

```json
{"email": "not-an-email", "password": "short"}
```

FastAPI + Pydantic reject it **before your route code runs** and return:

```json
{
  "detail": [
    {"loc": ["body", "email"], "msg": "value is not a valid email address", ...},
    {"loc": ["body", "password"], "msg": "String should have at least 8 characters", ...}
  ]
}
```

You get this validation for free — no `if len(password) < 8` anywhere.

### Special Validators

| Type | What It Validates |
|------|------------------|
| `EmailStr` | RFC-compliant email format (requires the `email-validator` package) |
| `Field(..., min_length=8)` | Minimum string length. The `...` means "required" (no default). |
| `Optional[str] = None` | Field can be omitted or `null` — defaults to `None` |

### Response Serialization

```python
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
```

When used with `response_model=UserResponse`:

```python
@router.post("/register", response_model=UserResponse, status_code=201)
def register(...):
    ...
    return UserResponse(id=user.id, email=user.email, ...)
```

This does two things:
1. **Filters the response** — only fields defined in `UserResponse` are included. Even if your `User` ORM object has `hashed_password`, it won't leak into the response.
2. **Generates documentation** — Swagger UI shows the exact response shape clients should expect.

### Why Schemas Are Separate from Models

You might wonder: "The `User` model already has `email`, `full_name`, etc. — why create `UserResponse` separately?"

Because they serve different purposes:

| | ORM Model (`models/user.py`) | Pydantic Schema (`schemas/auth.py`) |
|--|------|--------|
| **Purpose** | Maps to a database table | Defines an API contract |
| **Contains** | Everything in the DB (including `hashed_password`) | Only what the client should see |
| **Used by** | SQLAlchemy (internal) | FastAPI (external-facing) |

This separation is intentional. Your database schema and your API contract evolve independently. You might add a column to the database without exposing it to the API, or reshape the API response without touching the database.

---

## The Layered Architecture: Routes and Services

This project follows a two-layer pattern. Each layer has a strict job:

```
Route (thin)         → HTTP concerns: parse request, return response, status codes
Service (thick)      → Business logic: validation, database queries, processing
```

There is no controller layer. Routes call services directly. Controllers were removed because they were pass-throughs that added indirection without adding value — a common over-engineering trap in small-to-medium projects.

### When to add a controller layer

Controllers make sense when you have multiple transport layers (REST + GraphQL + WebSocket) sharing the same orchestration logic, or when request/response transformation is complex enough to warrant its own layer. This project has a single REST API with straightforward transformations, so routes delegate directly to services.

### How It Looks in Practice

Let's trace a real example — creating a conversation:

**Route** (`src/routes/conversation_routes.py`):
```python
@router.post("")
async def create_conversation(
    payload: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = conversation_service.create_conversation(db, user_id=current_user.id, title=payload.title)
    return {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()}
```

The route's job: extract parameters from the HTTP request, run auth, call the service, and format the response. It knows nothing about how conversations are stored.

**Service** (`src/services/conversation_service.py`):
```python
def create_conversation(self, db: Session, user_id: str, title: Optional[str] = None):
    conversation = Conversation(title=title, user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation
```

The service's job: actual business logic and database operations. Services are where the real work lives. They're also the most reusable — the `ConversationService` could be called from a CLI tool, a WebSocket handler, or a background job without any HTTP dependency.

### Service-to-Service Orchestration

When a feature needs to coordinate multiple services, that orchestration lives in a service method — not in the route. The `conversation_service.ask()` method is a good example:

```python
def ask(self, db, conversation_id, question, user_id):
    # 1. Load conversation history
    history = self.get_history(db, conversation_id, user_id=user_id)

    # 2. Save the user's question
    self.add_message(db, conversation_id, MessageRole.USER, question, ...)

    # 3. Run RAG query with history context (calls query_service)
    result = query_service.ask_with_sources(question, chat_history=history)

    # 4. Save the assistant's answer
    self.add_message(db, conversation_id, MessageRole.ASSISTANT, result["answer"], ...)

    # 5. Return result
    return {"conversation_id": conversation_id, "answer": result["answer"], "sources": result["sources"]}
```

This method coordinates `ConversationService` (own methods) and `QueryService` in a specific sequence. The route stays thin — it just calls `conversation_service.ask(...)` and returns the result.

### Singleton Instances

Every service is instantiated once at module level:

```python
# Bottom of each service file
conversation_service = ConversationService()
file_service = FileService()
```

Routes import these singletons directly. There's no per-request instantiation. This works because services are stateless — they don't store request-specific data on `self`.

---

## File Uploads: Handling Binary Data

File uploads use FastAPI's `UploadFile` — a wrapper around the raw file stream that provides metadata and efficient reading.

### How UploadFile Works

```python
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
```

**`UploadFile = File(...)`** tells FastAPI: "this endpoint accepts `multipart/form-data` with a file field." The `...` means it's required.

An `UploadFile` object gives you:

| Attribute | What It Is |
|-----------|-----------|
| `file.filename` | Original filename from the client (e.g., `"report.pdf"`) |
| `file.content_type` | MIME type (e.g., `"application/pdf"`) |
| `file.file` | The underlying file-like object (SpooledTemporaryFile) |

### Chunked Writing

The file service doesn't read the entire file into memory at once:

```python
FILE_WRITE_CHUNK_SIZE = 1024 * 1024  # 1 MB

with file_path.open("wb") as buffer:
    while chunk := file.file.read(FILE_WRITE_CHUNK_SIZE):
        buffer.write(chunk)
```

**Why chunked?** A user could upload a 50MB PDF. Reading 50MB into memory at once (with `file.file.read()`) would spike your server's RAM. Reading 1MB at a time keeps memory usage constant regardless of file size.

**The walrus operator (`:=`)** assigns and checks in one expression. `chunk := file.file.read(...)` reads a chunk, assigns it to `chunk`, and the `while` loop continues until `read()` returns an empty `bytes` object (meaning end of file).

### Validation Before Writing

Before any bytes touch the disk, the file is validated:

```python
def _validate_file(self, file: UploadFile) -> None:
    # Check MIME type against allowlist
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise FileValidationError(f"File type {file.content_type} is not allowed")

    # Check file size without reading content into memory
    file.file.seek(0, os.SEEK_END)     # Jump to end of file
    file_size = file.file.tell()        # Current position = total size
    file.file.seek(0)                   # Reset to beginning for later reading

    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise FileValidationError(f"File exceeds maximum size of {max_size_mb} MB")
```

**The seek/tell trick:** Instead of reading the entire file to count bytes, we jump the cursor to the end (`seek(0, SEEK_END)`), check the position (`tell()`), and jump back (`seek(0)`). This gives us the file size in three calls, with zero memory overhead.

### Cleanup on Failure

```python
try:
    # write file...
except Exception as exc:
    if file_path.exists():
        file_path.unlink()    # Delete the partially-written file
    raise FileValidationError("File storage failed") from exc
```

If writing fails halfway, we don't leave corrupt files on disk. The `finally` pattern would also work here, but since we only want to delete on failure (not on success), `except` is the right choice.

---

## Background Tasks: Fire-and-Forget Work

Document ingestion (parsing, chunking, summarizing, vectorizing) takes minutes. You don't want the user staring at a loading spinner for that long.

### How BackgroundTasks Work

```python
@router.post("/process/{file_id}")
async def process_file(
    file_id: str,
    background_tasks: BackgroundTasks,    # FastAPI injects this automatically
    current_user: User = Depends(get_current_user),
):
    return process_service.process_file_async(file_id, background_tasks)
```

**`BackgroundTasks`** is a special FastAPI class. When you add a task to it, FastAPI runs that function **after** the response is sent to the client:

```python
def process_file_async(self, file_id, background_tasks):
    # Immediately mark as "processing"
    self._write_status(file_id, DocumentStatus.PROCESSING)

    # Schedule the heavy work for AFTER the response
    background_tasks.add_task(self._run_pipeline, file_id, str(file_path))

    # Return immediately — client gets this in milliseconds
    return {
        "file_id": file_id,
        "status": "processing",
        "message": "Processing started. Poll /files/status/{file_id} for updates.",
    }
```

The flow:

```
Client sends POST /files/process/abc-123
  → Server responds: {"status": "processing"} (instant)
  → Server runs _run_pipeline() in the background (minutes)
  → Client polls GET /files/status/abc-123 periodically
  → Eventually gets {"status": "processed"} or {"status": "failed"}
```

### Status Tracking via JSON Files

Processing status is tracked via JSON files on disk — not in the database:

```python
def _write_status(self, file_id, status_value, error=None):
    payload = {"file_id": file_id, "status": status_value.value}
    if error:
        payload["error"] = error
    self._status_path(file_id).write_text(json.dumps(payload))
```

**Why not the database?** The background task runs outside the request lifecycle, so it doesn't have the request-scoped `Session` from `get_db()`. Using simple JSON files avoids the complexity of managing a separate database session in background threads.

### BackgroundTasks vs Celery

`BackgroundTasks` runs inside the same process as your API. It's fine for this project because:
- Tasks are infrequent (users don't upload hundreds of files per second)
- If the server restarts mid-task, re-triggering is acceptable

For high-volume production workloads, you'd swap this for Celery with Redis/RabbitMQ — but that's a different level of complexity.

---

## Exception Handling: One Pattern for All Errors

Instead of scattering `try/except` and `HTTPException` throughout routes, this project uses a **class hierarchy** and a **single global handler**.

### The Exception Hierarchy

```python
# src/core/exceptions.py
class AppError(Exception):
    status_code: int = 500
    def __init__(self, message="An application error occurred"):
        self.message = message

class AuthenticationError(AppError):
    status_code = 401

class ForbiddenError(AppError):
    status_code = 403

class FileValidationError(AppError):
    status_code = 400

class DocumentNotFoundError(AppError):
    status_code = 404

class ConflictError(AppError):
    status_code = 409

class ProcessingError(AppError):
    status_code = 422

class VectorStoreError(AppError):
    status_code = 503
```

Each error class declares its own HTTP status code. No lookup tables, no if/else chains.

### The Global Handler

```python
# src/main.py
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

This single handler catches **every** `AppError` subclass. When any service raises `AuthenticationError("Invalid token")`, the handler catches it and returns:

```json
HTTP 401
{"detail": "Invalid token"}
```

### How Services Use It

Services just `raise` — they never build HTTP responses:

```python
# In a service (no HTTP knowledge)
if not user:
    raise AuthenticationError("User not found")
```

This is clean separation. The service knows "something went wrong" and picks the right error type. The global handler translates that into an HTTP response. The service never imports `JSONResponse` or knows about HTTP status codes.

### Why Not Just Use HTTPException?

FastAPI's built-in `HTTPException` works, but it couples your services to HTTP:

```python
# Using HTTPException (couples service to HTTP)
from fastapi import HTTPException
raise HTTPException(status_code=401, detail="User not found")
```

If you later call that service from a CLI tool or background task, the `HTTPException` makes no sense — there's no HTTP context. Custom exceptions are transport-agnostic.

---

## Lifecycle Events: Startup and Shutdown

### Startup

```python
@app.on_event("startup")
async def on_startup():
    if settings.SECRET_KEY == "change-this-to-a-long-random-secret-in-production":
        logger.warning("SECRET_KEY is the insecure default ...")
    init_db()
```

This runs **once** when the server starts, before any request is handled. It:

1. Checks for the insecure default `SECRET_KEY` and logs a warning
2. Calls `init_db()` to create database tables if they don't exist

**Why here and not at module import time?** Because `init_db()` has side effects (it talks to the database). Running it at import time would make testing harder and could fail during module collection. The startup event gives you a controlled, predictable place for initialization.

> **Note:** `@app.on_event("startup")` works but is considered legacy in newer FastAPI. The modern approach is `lifespan` context managers. The current code works fine — just be aware if you see `lifespan` in newer tutorials.

---

## Async vs Sync: When It Matters

You'll notice something in this project — routes are `async def` but the underlying services are regular `def`:

```python
# Route: async
@router.post("/upload")
async def upload_file(file: UploadFile = File(...), ...):
    file_id = file_service.save_upload(file)   # calls sync code
    return JSONResponse(...)

# Service: sync
def save_upload(self, file: UploadFile) -> str:
    self._validate_file(file)                  # blocking I/O
    # ... write file to disk ...
    return doc_id
```

### How FastAPI Handles This

FastAPI handles both `async def` and regular `def` routes:

| Route Type | FastAPI Behavior |
|-----------|-----------------|
| `async def` | Runs directly on the event loop. If you call blocking code inside, **it blocks the entire server**. |
| `def` | FastAPI automatically runs it in a **thread pool**, so blocking code doesn't freeze other requests. |

In this project, routes are declared as `async def` but call synchronous services (database queries via SQLAlchemy, file I/O). FastAPI doesn't automatically offload the *internal* blocking calls from an `async def` route — only entire `def` routes get the thread pool treatment.

**Why does this work anyway?** Because:
- SQLAlchemy with SQLite using `StaticPool` is fast enough that the blocking is brief
- File I/O with chunked reads is also quick
- This is a single-user/low-traffic application

For high-concurrency production, you'd either use `def` routes (letting FastAPI's thread pool handle them) or use `async` SQLAlchemy with `asyncpg`.

### The Event Loop: How `await` Actually Works

Every `await` in FastAPI (or any asyncio Python code) follows the same pattern:

```python
response = await call_next(request)   # coroutine pauses HERE
# ... resumes here when call_next finishes
```

1. The coroutine **pauses** at `await`
2. **Control returns to the event loop**
3. The event loop decides what to run next

The event loop is a **single-threaded task manager** that juggles all your coroutines:

```
Event Loop (single thread)
  │
  ├── Request A middleware: paused at await call_next()
  ├── Request B route: paused at await db.execute()
  ├── Request C route: READY → run this one now
  └── Request D middleware: paused at await redis.get()
```

It continuously cycles through all coroutines, running whichever ones are ready and parking the ones that are waiting for I/O.

**How different `await` targets are handled:**

| What you `await` | What happens under the hood |
|-------------------|---------------------------|
| I/O (DB query, HTTP call, file read) | Event loop asks the OS to notify when I/O completes. Meanwhile, runs other coroutines. |
| `asyncio.sleep()` | Event loop sets a timer, runs other coroutines until timer fires. |
| Thread pool task (`run_in_executor`) | Work runs on a separate thread. Event loop checks when the thread finishes. |
| Another coroutine | That coroutine runs until it hits its own `await`, then control bounces back. |

**The critical insight:** `await` does **not** create a new thread. The event loop runs on a single thread and handles concurrency by rapidly switching between coroutines at their `await` points. This is why FastAPI can handle thousands of concurrent requests without thousands of threads — as long as you're doing I/O, not CPU work.

**Analogy:** The event loop is a chef with many pots on the stove. When pot A is simmering (`await`), the chef stirs pot B. When pot B needs to bake (`await`), the chef checks if pot A is done. One chef, many dishes, no idle time — but if the chef has to hand-knead dough (CPU-bound blocking), every other pot burns.

That's exactly why calling sync/blocking code inside `async def` is dangerous — it's the dough-kneading problem. The single-threaded event loop can't switch to other requests while your blocking code runs.

---

## API Documentation: Free Swagger UI

FastAPI generates interactive API documentation automatically from your code. No extra work required.

### Swagger UI — `/docs`

Visit `http://localhost:8000/docs` in your browser. You'll see:

- Every endpoint grouped by `tags` (Auth, Files, Processing, Query, Conversations)
- Request/response schemas generated from your Pydantic models
- An "Authorize" button for entering your JWT token
- A "Try it out" button on every endpoint for live testing

### How It Gets Its Information

| Swagger UI shows | Comes from |
|-----------------|-----------|
| Endpoint grouping | `tags=["Auth"]` on the router |
| Endpoint description | `summary="..."` on the decorator |
| Request body schema | Pydantic model type hints (`RegisterRequest`) |
| Response schema | `response_model=UserResponse` |
| Auth requirement | `Depends(get_current_user)` triggers the lock icon |
| Login URL for Authorize | `OAuth2PasswordBearer(tokenUrl="/auth/login")` |

### Authentication in Swagger

1. Call `POST /auth/login` with your credentials
2. Copy the `access_token` from the response
3. Click the "Authorize" button (top right)
4. Paste the token and click "Authorize"
5. All subsequent requests will include the `Authorization: Bearer <token>` header

---

## Endpoint Reference

### Auth (`/auth`)

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| POST | `/auth/register` | No | `RegisterRequest` (JSON) | `UserResponse` | 201 |
| POST | `/auth/login` | No | `OAuth2PasswordRequestForm` (form) | `TokenResponse` | 200 |
| GET | `/auth/me` | Yes | — | `UserResponse` | 200 |

### Files (`/files`)

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| POST | `/files/upload` | Yes | `multipart/form-data` (single file) | `{message, file_id}` | 201 |
| POST | `/files/upload/multiple` | Yes | `multipart/form-data` (multiple files) | `{message, files[]}` | 201 |
| DELETE | `/files/delete?file_id=...` | Yes | Query param: `file_id` | `{message, file_id}` | 200 |

### Processing (`/files`)

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| POST | `/files/process/{file_id}` | Yes | Path param | `{file_id, status, message}` | 200 |
| GET | `/files/status/{file_id}` | Yes | Path param | `{file_id, status}` | 200 |

### Query (`/query`)

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| POST | `/query/ask` | Yes | `QueryRequest` (JSON) | `{answer, sources[]}` | 200 |

### Conversations (`/conversations`)

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| POST | `/conversations` | Yes | `CreateConversationRequest` (JSON) | `{id, title, created_at}` | 200 |
| GET | `/conversations` | Yes | — | `[{id, title, message_count, ...}]` | 200 |
| GET | `/conversations/{id}/messages` | Yes | — | `[{id, role, content, sources, ...}]` | 200 |
| POST | `/conversations/{id}/ask` | Yes | `ChatRequest` (JSON) | `{conversation_id, answer, sources[]}` | 200 |
| DELETE | `/conversations/{id}` | Yes | — | `{message, id}` | 200 |
