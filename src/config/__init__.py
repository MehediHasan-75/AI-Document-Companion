"""
Configuration Package.

Centralized configuration management using Pydantic Settings.
All configuration values are loaded from environment variables or .env file.

Usage:
    >>> from src.config import settings
    >>> print(settings.OLLAMA_HOST)
"""

from src.config.environment import Settings

# Singleton settings instance
settings = Settings()

__all__ = ["Settings", "settings"]