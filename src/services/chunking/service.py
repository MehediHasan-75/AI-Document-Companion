
"""
src/services/chunking/service.py
──────────────────────────────────
Public facade — the only import ingestion_service.py needs.

Usage:
    from src.services.chunking import ChunkingService

    svc    = ChunkingService()
    result = svc.process("paper.pdf")

    result.text_chunks    # List[TextChunk]
    result.table_chunks   # List[TableChunk]
    result.image_chunks   # List[ImageChunk]
"""
from __future__ import annotations

import logging
from typing import List, Optional

from .models import PDFChunkResult
from .partitioner import PDFPartitioner
from .strategy import ChunkingStrategy, HiResStrategy

logger = logging.getLogger(__name__)


class ChunkingService:
    def __init__(self, strategy: ChunkingStrategy = None) -> None:
        self._partitioner = PDFPartitioner(strategy or HiResStrategy)

    def process(self, file_path: str, paper_name: Optional[str] = None) -> PDFChunkResult:
        """Partition a single PDF. Returns PDFChunkResult."""
        return self._partitioner.partition(file_path, paper_name=paper_name)

    def process_many(self, file_paths: List[str], fail_fast: bool = False) -> List[PDFChunkResult]:
        """Partition multiple PDFs. Skips failures unless fail_fast=True."""
        results = []
        for path in file_paths:
            try:
                results.append(self.process(path))
            except Exception as exc:
                logger.error("Failed to process '%s': %s", path, exc)
                if fail_fast:
                    raise
        logger.info("Processed %d/%d files.", len(results), len(file_paths))
        return results