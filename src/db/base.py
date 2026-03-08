"""
SQLAlchemy Declarative Base and Common Mixins.

This module provides the foundation for all database models in the application.
It defines the declarative base class and common mixins used across models.

Architecture:
    - Uses SQLAlchemy 2.0 style with mapped_column
    - UUID primary keys for distributed systems compatibility
    - Timestamp mixins for auditing
    - PostgreSQL-ready with SQLite fallback for development

Integration Points:
    - ALEMBIC_INTEGRATION: Database migrations
    - POSTGRES_INTEGRATION: Production database

Example:
    >>> from src.db.base import Base, TimestampMixin
    >>> class MyModel(Base, TimestampMixin):
    ...     __tablename__ = "my_table"
    ...     id = mapped_column(String, primary_key=True)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# =============================================================================
# Declarative Base
# =============================================================================

class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for all models.
    
    All database models should inherit from this class to be
    properly registered with SQLAlchemy's metadata.
    
    Example:
        >>> class Document(Base):
        ...     __tablename__ = "documents"
        ...     id: Mapped[str] = mapped_column(primary_key=True)
    """
    pass


# =============================================================================
# Common Mixins
# =============================================================================

class UUIDMixin:
    """
    Mixin providing a UUID primary key.
    
    Generates a UUID4 string as the primary key for models.
    Suitable for distributed systems where auto-increment IDs
    could cause conflicts.
    
    Attributes:
        id: UUID4 string primary key.
    """
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )


class TimestampMixin:
    """
    Mixin providing created_at and updated_at timestamps.
    
    Automatically sets created_at on insert and updates
    updated_at on every modification.
    
    Attributes:
        created_at: Timestamp when record was created.
        updated_at: Timestamp when record was last updated.
    
    Note:
        Uses server-side defaults where supported (PostgreSQL).
        Falls back to Python-side defaults for SQLite.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )


class SoftDeleteMixin:
    """
    Mixin providing soft delete functionality.
    
    Instead of permanently deleting records, marks them as deleted
    with a timestamp. Useful for audit trails and data recovery.
    
    Attributes:
        deleted_at: Timestamp when record was soft-deleted, or None.
        is_deleted: Computed property indicating deletion status.
    """
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None
    )
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None

