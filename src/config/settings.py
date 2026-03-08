"""
Backward-compatible settings module.

Prefer importing configuration from ``src.config.environment`` instead of this
module. This file simply re‑exports the canonical ``Settings`` class and
``env`` instance for any legacy imports.
"""

from src.config.environment import Settings, env

__all__ = ["Settings", "env"]