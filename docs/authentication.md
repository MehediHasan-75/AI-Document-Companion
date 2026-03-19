# Authentication System

## Overview

The app uses stateless JWT Bearer authentication. Users register with email/password, receive a JWT on login, and include it in the `Authorization: Bearer <token>` header for all protected endpoints.

## Architecture

```
                    +---------------+
                    |    Client     |
                    +-------+-------+
                            | Authorization: Bearer <token>
                    +-------v-------+
                    |    FastAPI    |
                    |   Middleware   | (CORS, GZip, logging)
                    +-------+-------+
                            |
               +------------v-------------+
               |  OAuth2PasswordBearer    | extracts token from header
               |  dependencies/auth.py    |
               +------------+-------------+
                            |
               +------------v-------------+
               |      decode_token()      | verify JWT signature + exp
               |  services/auth_service   |
               +------------+-------------+
                            |
               +------------v-------------+
               | auth_service.get_by_id   | load User from DB,
               |                          | check is_active
               +------------+-------------+
                            |
                    +-------v-------+
                    | Route Handler | receives User object
                    +---------------+
```

### Components

| Component | File | Responsibility |
|-----------|------|----------------|
| Routes | `src/routes/auth_routes.py` | `/auth/register`, `/auth/login`, `/auth/me` |
| Dependency | `src/dependencies/auth.py` | `get_current_user` — extracts and validates JWT, returns `User` |
| Service | `src/services/auth_service.py` | Password hashing, JWT creation/decode, user CRUD |
| Schemas | `src/schemas/auth.py` | `RegisterRequest`, `TokenResponse`, `UserResponse` |
| Model | `src/models/user.py` | `User` ORM (email, hashed_password, full_name, is_active) |
| Exceptions | `src/core/exceptions.py` | `AuthenticationError` (401), `ForbiddenError` (403), `ConflictError` (409) |

## API Endpoints

### POST /auth/register

Register a new user account.

- **Auth required:** No
- **Request body (JSON):**
  ```json
  {
    "email": "user@example.com",
    "password": "securepass123",
    "full_name": "John Doe"
  }
  ```
  - `email` — valid email address (required)
  - `password` — 8 to 128 characters (required)
  - `full_name` — optional
- **Response (201):**
  ```json
  {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2026-03-18T12:00:00"
  }
  ```
- **Errors:** 409 (email already registered), 422 (validation failure)

### POST /auth/login

Authenticate and receive a JWT token.

- **Auth required:** No
- **Request body (form-encoded, not JSON):**
  - `username` — email address
  - `password` — account password
- **Response (200):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```
- **Errors:** 401 (invalid credentials)

### GET /auth/me

Get the current authenticated user's profile.

- **Auth required:** Yes (`Authorization: Bearer <token>`)
- **Response (200):**
  ```json
  {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2026-03-18T12:00:00"
  }
  ```
- **Errors:** 401 (invalid/expired token), 403 (account deactivated)

## Auth Flow Step-by-Step

1. **Register** — `POST /auth/register` with email + password (8+ chars). Password is bcrypt-hashed (12 rounds) and stored. Returns user info (no token).
2. **Login** — `POST /auth/login` with form-encoded `username` (email) + `password`. Server verifies against bcrypt hash, issues JWT with claims `{sub, email, iat, exp, jti}`.
3. **Authenticated requests** — Client sends `Authorization: Bearer <token>`. FastAPI's `OAuth2PasswordBearer` extracts it, `decode_token()` verifies signature and expiration, then `get_by_id()` confirms user exists and is active.
4. **Token expiry** — After 24 hours the token is rejected. Client must re-login.
5. **Deactivated user** — Returns 403 even with a valid token.

## Security Measures

### Implemented

- bcrypt password hashing (12 rounds, explicit)
- JWT with HS256 signing, `exp`/`iat`/`jti` claims
- Password min 8 / max 128 character validation at schema level
- User active-status check on every authenticated request
- Generic error messages (no email enumeration)
- CORS middleware
- 401/403 differentiation (expired token vs deactivated account)
- Startup warning when SECRET_KEY is the insecure default

### Recommended for Production

- **Rate limiting** on `/auth/login` (e.g., `slowapi` — 5 attempts/min per IP)
- **Refresh token rotation** — short-lived access (15m) + long-lived refresh (7d) stored in DB
- **Token blacklist** — for logout/revocation (Redis or DB table keyed by `jti`)
- **CORS lockdown** — replace `["*"]` default with actual frontend origin(s)
- **Strong SECRET_KEY** — generate with `openssl rand -hex 32`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-this-to-a-long-random-secret-in-production` | JWT signing key. **Must override in production.** Generate with `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours) | Token lifetime in minutes |

## Testing Guide

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# Login (form-encoded, not JSON)
curl -X POST http://localhost:8000/auth/login \
  -d "username=user@example.com&password=securepass123"

# Use the token from login response
TOKEN="<access_token from login response>"

# Get current user
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

Swagger UI is also available at `http://localhost:8000/docs` with a built-in "Authorize" button for Bearer token input.

## Common Errors

| Status | Error | Cause |
|--------|-------|-------|
| 401 | Unauthorized | Missing token, invalid/expired token, wrong credentials, user not found |
| 403 | Forbidden | Account has been deactivated |
| 409 | Conflict | Email already registered |
| 422 | Validation Error | Password too short (<8 chars) or too long (>128 chars), invalid email format |
