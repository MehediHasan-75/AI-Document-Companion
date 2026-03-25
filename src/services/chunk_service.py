"""Chunk processing utilities for separating document elements by type."""

from __future__ import annotations

import logging
from typing import List, Tuple

from unstructured.documents.elements import Element

logger = logging.getLogger(__name__)


def _element_type(el: Element) -> str:
    return type(el).__name__


def _extract_base64(el: Element) -> str | None:
    meta = getattr(el, "metadata", None)
    return getattr(meta, "image_base64", None) if meta else None


def separate_elements(
    chunks: List[Element],
) -> Tuple[List[Element], List[Element]]:
    """Separate document chunks into text (CompositeElement) and table elements.

    chunk_by_title() can wrap Table elements inside CompositeElement.orig_elements.
    Those nested tables are extracted separately so they are summarized as tables
    (with text_as_html) rather than being lost inside a text chunk.
    """
    texts: List[Element] = []
    tables: List[Element] = []

    for chunk in chunks:
        name = _element_type(chunk)
        if name in ("Table", "TableChunk"):
            tables.append(chunk)
        elif name == "CompositeElement":
            texts.append(chunk)
            # Also pull out any Table elements nested in orig_elements
            orig = getattr(getattr(chunk, "metadata", None), "orig_elements", None)
            if orig:
                for el in orig:
                    if _element_type(el) in ("Table", "TableChunk"):
                        tables.append(el)

    logger.debug(
        "Separated %d chunks into %d texts and %d tables",
        len(chunks),
        len(texts),
        len(tables),
    )
    return texts, tables


def extract_images_base64(chunks: List[Element]) -> List[str]:
    """Extract all base64-encoded images from chunks.

    Collects images from two sources:
    - Standalone Image elements produced by chunk_by_title()
    - Image elements nested inside CompositeElement.metadata.orig_elements
    """
    images_b64: List[str] = []

    for chunk in chunks:
        name = _element_type(chunk)

        # Standalone Image element
        if name == "Image":
            b64 = _extract_base64(chunk)
            if b64:
                images_b64.append(b64)
            continue

        # Images nested inside a CompositeElement
        if name == "CompositeElement":
            orig = getattr(getattr(chunk, "metadata", None), "orig_elements", None)
            if not orig:
                continue
            for el in orig:
                if _element_type(el) == "Image":
                    b64 = _extract_base64(el)
                    if b64:
                        images_b64.append(b64)

    logger.debug("Extracted %d base64-encoded images", len(images_b64))
    return images_b64
