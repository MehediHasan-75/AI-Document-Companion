"""Document partitioning service using the Unstructured library."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element

from src.config.constants import (
    DEFAULT_PARTITION_STRATEGY,
    DEFAULT_MAX_CHARACTERS,
    DEFAULT_COMBINE_UNDER_N_CHARS,
    DEFAULT_NEW_AFTER_N_CHARS,
    DEFAULT_IMAGE_TYPES,
)

logger = logging.getLogger(__name__)


def partition_document(
    file_path: str,
    strategy: str = DEFAULT_PARTITION_STRATEGY,
    max_characters: int = DEFAULT_MAX_CHARACTERS,
    combine_text_under_n_chars: int = DEFAULT_COMBINE_UNDER_N_CHARS,
    new_after_n_chars: int = DEFAULT_NEW_AFTER_N_CHARS,
    extract_images: bool = True,
) -> List[Element]:
    """Partition a document into structured elements with title-based chunking."""
    logger.info("Partitioning document: %s (strategy=%s)", file_path, strategy)

    if not Path(file_path).is_file():
        raise FileNotFoundError(f"Document not found at: {file_path}")

    extract_kwargs = {}
    if extract_images:
        extract_kwargs = {
            "pdf_extract_image_block_types": DEFAULT_IMAGE_TYPES,
            "pdf_extract_image_block_to_payload": True,
        }

    elements = partition(
        filename=file_path,
        strategy=strategy,
        infer_table_structure=True,
        **extract_kwargs,
    )

    chunks = chunk_by_title(
        elements,
        max_characters=max_characters,
        combine_text_under_n_chars=combine_text_under_n_chars,
        new_after_n_chars=new_after_n_chars,
    )

    logger.info("Partitioning complete: %d chunks generated from %s", len(chunks), file_path)
    return chunks
