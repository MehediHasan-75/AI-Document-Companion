"""Shared database dependency for FastAPI routes."""

from src.db.session import get_db

__all__ = ["get_db"]
