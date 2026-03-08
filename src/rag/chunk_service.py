"""
Facade for utilities that operate on Unstructured chunks.

Delegates to the existing implementation in ``src.services.chunk_service``.
"""

from src.services.chunk_service import separate_elements, get_images_base64

__all__ = ["separate_elements", "get_images_base64"]

