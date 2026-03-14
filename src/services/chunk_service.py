"""Chunk processing utilities for separating document elements by type."""

from __future__ import annotations

import logging
from typing import Any, List, Tuple

from unstructured.documents.elements import Element

logger = logging.getLogger(__name__)


def separate_elements(chunks: List[Element]) -> Tuple[List[Element], List[Element]]:
    """Separate document chunks into text (CompositeElement) and table elements."""
    tables: List[Element] = []
    texts: List[Element] = []

    for chunk in chunks:
        chunk_type = str(type(chunk))
        if "Table" in chunk_type:
            tables.append(chunk)
        if "CompositeElement" in chunk_type:
            texts.append(chunk)

    logger.debug(
        "Separated %d chunks into %d texts and %d tables",
        len(chunks),
        len(texts),
        len(tables),
    )
    return texts, tables


def get_images_base64(chunks: List[Element]) -> List[str]:
    """Extract base64-encoded images from CompositeElement chunks."""
    images_b64: List[str] = []

    for chunk in chunks:
        if "CompositeElement" not in str(type(chunk)):
            continue
        for el in chunk.metadata.orig_elements:
            if "Image" in str(type(el)):
                if hasattr(el.metadata, "image_base64") and el.metadata.image_base64:
                    images_b64.append(el.metadata.image_base64)

    logger.debug("Extracted %d base64-encoded images", len(images_b64))
    return images_b64
