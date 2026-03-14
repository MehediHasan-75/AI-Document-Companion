"""Shared database dependency for FastAPI routes."""

from typing import Generator

from sqlalchemy.orm import Session

from src.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
