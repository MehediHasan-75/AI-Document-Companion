"""
Chunk Processing Utilities for Document Elements.

This module provides utilities for processing and separating document chunks
produced by the Unstructured library. It handles the classification of
extracted elements into text, tables, and images.

Architecture:
    - Works with Unstructured Element types
    - Separates elements by type for different processing pipelines
    - Extracts embedded images as base64 for vision model processing

Integration Points:
    - MQ_INTEGRATION: Could stream chunks to processing queue
    - WEBSOCKET_INTEGRATION: Emit chunk processing progress

Example:
    >>> from src.services.chunk_service import separate_elements, get_images_base64
    >>> chunks = partition_document("doc.pdf")
    >>> texts, tables = separate_elements(chunks)
    >>> images = get_images_base64(chunks)
"""

from __future__ import annotations

import logging
from typing import Any, List, Tuple


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Element Separation
# =============================================================================

def separate_elements(chunks: List[Any]) -> Tuple[List[Any], List[Any]]:
    """
    Separate document chunks into text-like elements and table elements.
    
    Classifies Unstructured elements by their type, separating tables
    (which need special HTML processing) from composite text elements
    (which contain the main document content).
    
    Args:
        chunks: List of Unstructured Element objects from partition_document.
            Expected types include CompositeElement, Table, Title, etc.
    
    Returns:
        Tuple containing:
            - texts: List of CompositeElement objects (text content)
            - tables: List of Table objects (tabular data)
    
    Integration Points:
        - WEBSOCKET_INTEGRATION: Emit element counts during processing
    
    Example:
        >>> chunks = partition_document("report.pdf")
        >>> texts, tables = separate_elements(chunks)
        >>> print(f"Found {len(texts)} text sections, {len(tables)} tables")
    
    Note:
        Type detection uses string matching on class names to maintain
        compatibility across Unstructured library versions.
    """
    tables: List[Any] = []
    texts: List[Any] = []
    
    for chunk in chunks:
        chunk_type = str(type(chunk))
        
        # Tables need special handling (HTML extraction)
        if "Table" in chunk_type:
            tables.append(chunk)
        
        # CompositeElements contain merged text content
        if "CompositeElement" in chunk_type:
            texts.append(chunk)
    
    logger.debug(
        "Separated %d chunks into %d texts and %d tables",
        len(chunks), len(texts), len(tables)
    )
    
    return texts, tables


# =============================================================================
# Image Extraction
# =============================================================================

def get_images_base64(chunks: List[Any]) -> List[str]:
    """
    Extract base64-encoded images from document chunks.
    
    Iterates through CompositeElement chunks to find embedded Image
    elements and extracts their base64-encoded data for processing
    by vision models.
    
    Args:
        chunks: List of Unstructured Element objects from partition_document.
            Images are typically nested within CompositeElement metadata.
    
    Returns:
        List of base64-encoded image strings ready for vision model input.
    
    Integration Points:
        - REDIS_INTEGRATION: Cache extracted images by content hash
        - MQ_INTEGRATION: Queue images for async vision processing
    
    Example:
        >>> chunks = partition_document("report.pdf")
        >>> images = get_images_base64(chunks)
        >>> print(f"Extracted {len(images)} images")
        >>> # Each image is base64: "iVBORw0KGgo..."
    
    Note:
        Only extracts images from CompositeElement types. Images are
        stored in element.metadata.orig_elements as nested Image elements.
    """
    images_b64: List[str] = []
    
    for chunk in chunks:
        # Only CompositeElements contain nested original elements
        if "CompositeElement" in str(type(chunk)):
            # Access original elements from chunk metadata
            chunk_els = chunk.metadata.orig_elements
            
            for el in chunk_els:
                # Check if element is an Image type
                if "Image" in str(type(el)):
                    # Extract base64 data from image metadata
                    if hasattr(el.metadata, 'image_base64') and el.metadata.image_base64:
                        images_b64.append(el.metadata.image_base64)
    
    logger.debug("Extracted %d base64-encoded images", len(images_b64))
    
    return images_b64
