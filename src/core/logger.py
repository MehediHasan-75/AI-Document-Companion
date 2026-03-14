"""Logging configuration for the application."""

import logging

from src.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(format=log_format, level=level, force=True)

    # Quiet noisy third-party loggers
    for name in ("httpx", "chromadb", "unstructured", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
