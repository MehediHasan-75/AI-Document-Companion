"""
Database Package.

This package provides database connectivity and ORM base classes
for the RAG system using SQLAlchemy 2.0.

Exports:
    Base Classes:
        - Base: SQLAlchemy declarative base
        - UUIDMixin: UUID primary key mixin
        - TimestampMixin: created_at/updated_at mixin
        - SoftDeleteMixin: deleted_at soft delete mixin
    
    Session Management:
        - create_db_engine: Create database engine
        - SessionLocal: Session factory
        - get_db: FastAPI dependency for database sessions
        - init_db: Initialize database tables
        - drop_db: Drop all database tables
"""

from src.db.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
from src.db.session import (
    create_db_engine,
    SessionLocal,
    get_db,
    init_db,
    drop_db,
)

__all__ = [
    # Base Classes
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    # Session Management
    "create_db_engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "drop_db",
]
