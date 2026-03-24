"""Database session management for FastAPI dependency injection."""

from __future__ import annotations

import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.base import Base

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL: str = "sqlite:///./app.db"


def get_database_url() -> str:
    """Get database URL from settings or use default SQLite."""
    try:
        from src.config import settings
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql"):
            # Fall back to SQLite if URL contains placeholders or points to localhost
            if "<" in db_url or "localhost" in db_url:
                logger.info("Using SQLite for development")
                return DEFAULT_DATABASE_URL
        return db_url
    except Exception:
        return DEFAULT_DATABASE_URL


def create_db_engine(database_url: str | None = None):
    """Create SQLAlchemy engine with appropriate configuration."""
    url = database_url or get_database_url()

    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        logger.info("SQLite engine created: %s", url)

    else:
        try:
            from src.config import settings
            pool_size = settings.DB_POOL_SIZE
            max_overflow = settings.DB_MAX_OVERFLOW
        except Exception:
            pool_size = 5
            max_overflow = 10

        engine = create_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=False,
        )
        logger.info("PostgreSQL engine created with pool_size=%d", pool_size)

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _apply_migrations() -> None:
    """Add columns that may be missing from existing SQLite databases."""
    migrations = [
        ("documents", "image_count", "INTEGER"),
        ("documents", "table_count", "INTEGER"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                    )
                )
                conn.commit()
                logger.info("Migration applied: added %s.%s", table, column)
            except Exception:
                pass  # column already exists


def init_db() -> None:
    """Create all database tables."""
    from src.models import document, conversation, message, chunk, user  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _apply_migrations()
    logger.info("Database tables created")


def drop_db() -> None:
    """Drop all database tables. WARNING: destructive."""
    Base.metadata.drop_all(bind=engine)
    logger.warning("Database tables dropped")
