"""
Database Session Management.

This module provides SQLAlchemy engine configuration and session management
for FastAPI dependency injection. Supports both SQLite (development) and
PostgreSQL (production).

Architecture:
    - Async-ready session factory (can be upgraded to async)
    - Connection pooling for production
    - FastAPI dependency for request-scoped sessions
    - Automatic table creation on startup

Configuration:
    - DATABASE_URL: Connection string (SQLite or PostgreSQL)
    - DB_POOL_SIZE: Connection pool size (PostgreSQL only)
    - DB_MAX_OVERFLOW: Max overflow connections

Integration Points:
    - POSTGRES_INTEGRATION: Production database
    - ALEMBIC_INTEGRATION: Database migrations
    - ASYNC_INTEGRATION: Upgrade to async sessions

Example:
    >>> from src.db.session import get_db, init_db
    >>> init_db()  # Create tables
    >>> 
    >>> @app.get("/items")
    >>> def get_items(db: Session = Depends(get_db)):
    ...     return db.query(Item).all()
"""

from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.base import Base


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)

# Default to SQLite for development
# Override with DATABASE_URL environment variable for production
DEFAULT_DATABASE_URL: str = "sqlite:///./app.db"


# =============================================================================
# Engine Configuration
# =============================================================================

def get_database_url() -> str:
    """
    Get database URL from environment or use default.
    
    Returns:
        Database connection string.
    
    Note:
        Imports env lazily to avoid circular imports.
    """
    try:
        from src.config.environment import env
        # Use SQLite for development if PostgreSQL is not configured
        db_url = env.DATABASE_URL
        if db_url.startswith("postgresql") and "localhost" in db_url:
            # Check if PostgreSQL is likely not running, fallback to SQLite
            logger.info("Using SQLite for development")
            return DEFAULT_DATABASE_URL
        return db_url
    except Exception:
        return DEFAULT_DATABASE_URL


def create_db_engine(database_url: str | None = None):
    """
    Create SQLAlchemy engine with appropriate configuration.
    
    Args:
        database_url: Database connection string. If None, uses environment.
    
    Returns:
        Configured SQLAlchemy engine.
    
    Note:
        SQLite requires special handling for threading and foreign keys.
        PostgreSQL uses connection pooling for production.
    """
    url = database_url or get_database_url()
    
    if url.startswith("sqlite"):
        # SQLite configuration for development
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,  # Single connection for SQLite
            echo=False  # Set True for SQL debugging
        )
        
        # Enable foreign key support for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        logger.info("SQLite engine created: %s", url)
        
    else:
        # PostgreSQL configuration for production
        try:
            from src.config.environment import env
            pool_size = env.DB_POOL_SIZE
            max_overflow = env.DB_MAX_OVERFLOW
        except Exception:
            pool_size = 5
            max_overflow = 10
        
        engine = create_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            echo=False
        )
        logger.info("PostgreSQL engine created with pool_size=%d", pool_size)
    
    return engine


# Create default engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# Session Dependency
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    
    Yields a database session that is automatically closed after the
    request completes. Use with FastAPI's Depends().
    
    Yields:
        SQLAlchemy Session instance.
    
    Example:
        >>> @app.get("/documents")
        >>> def list_documents(db: Session = Depends(get_db)):
        ...     return db.query(Document).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Database Initialization
# =============================================================================

def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    Creates all tables defined in models that inherit from Base.
    Safe to call multiple times - only creates tables that don't exist.
    
    Note:
        For production, use Alembic migrations instead of create_all().
    
    Example:
        >>> from src.db.session import init_db
        >>> init_db()  # Creates all tables
    """
    # Import models to ensure they're registered with Base
    from src.models import document, conversation, message, chunk  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data! Use only for testing/development.
    
    Example:
        >>> from src.db.session import drop_db
        >>> drop_db()  # Drops all tables
    """
    Base.metadata.drop_all(bind=engine)
    logger.warning("Database tables dropped")


