"""
Unstructured Document Partitioning Service.

This module provides a wrapper around the Unstructured library for parsing
various documents (PDF, DOCX, HTML, etc.) into structured elements.

Architecture:
    - Uses Unstructured's auto-partitioning for file type routing
    - Extracts images as base64 payloads for vision model processing (PDFs)
    - Applies title-based chunking universally for semantic coherence
    - Infers table structure for HTML representation

Configuration:
    - PARTITION_STRATEGY: "hi_res" (accurate) or "fast" (quick)
    - MAX_CHARACTERS: Maximum characters per chunk
    - COMBINE_TEXT_UNDER_N_CHARS: Merge small text blocks
    - NEW_AFTER_N_CHARS: Force new chunk after N characters
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

# Use the auto partitioner and unified chunking utilities
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)

DEFAULT_PARTITION_STRATEGY: str = "hi_res"
DEFAULT_MAX_CHARACTERS: int = 10000
DEFAULT_COMBINE_UNDER_N_CHARS: int = 2000
DEFAULT_NEW_AFTER_N_CHARS: int = 6000
DEFAULT_IMAGE_TYPES: List[str] = ["Image"]


# =============================================================================
# Document Partitioning
# =============================================================================

def partition_document(
    file_path: str,
    strategy: str = DEFAULT_PARTITION_STRATEGY,
    max_characters: int = DEFAULT_MAX_CHARACTERS,
    combine_text_under_n_chars: int = DEFAULT_COMBINE_UNDER_N_CHARS,
    new_after_n_chars: int = DEFAULT_NEW_AFTER_N_CHARS,
    extract_images: bool = True
) -> List[Element]:
    """
    Partition a document into structured elements using Unstructured.
    
    Extracts text, tables, and images from a document, organizing
    content into semantically coherent chunks for downstream processing.
    
    Args:
        file_path: Absolute path to the file to partition.
        strategy: Partitioning strategy to use ("hi_res", "fast", "auto").
        max_characters: Maximum characters per chunk before splitting.
        combine_text_under_n_chars: Merge text blocks smaller than this.
        new_after_n_chars: Force a new chunk after reaching this count.
        extract_images: Whether to extract images as base64 payloads (PDFs).
    
    Returns:
        List of Unstructured Element objects.
    
    Raises:
        FileNotFoundError: If the specified file does not exist.
    """
    logger.info("Partitioning document: %s (strategy=%s)", file_path, strategy)

    path_obj = Path(file_path)
    if not path_obj.is_file():
        raise FileNotFoundError(f"Document not found at: {file_path}")

    # REDIS_INTEGRATION: Check cache first
    # file_hash = compute_file_hash(file_path)
    # cached = get_cached_partition(file_hash)
    # if cached:
    #     logger.debug("Using cached partition result")
    #     return cached

    # Configure image extraction (Auto-partition routes these to PDF processing)
    extract_kwargs = {}
    if extract_images:
        extract_kwargs = {
            "pdf_extract_image_block_types": DEFAULT_IMAGE_TYPES,
            "pdf_extract_image_block_to_payload": True,
        }

    # 1. Partition the document (Automatically detects file type)
    elements = partition(
        filename=file_path,
        strategy=strategy,
        infer_table_structure=True,
        **extract_kwargs
    )

    # 2. Apply chunking universally to the extracted elements
    chunks = chunk_by_title(
        elements,
        max_characters=max_characters,
        combine_text_under_n_chars=combine_text_under_n_chars,
        new_after_n_chars=new_after_n_chars
    )

    logger.info(
        "Partitioning complete: %d chunks generated from %s",
        len(chunks), file_path
    )

    # REDIS_INTEGRATION: Cache the result
    # cache_partition(file_hash, chunks)

    return chunks