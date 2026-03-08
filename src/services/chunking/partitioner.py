"""
src/services/chunking/partitioner.py
──────────────────────────────────────
Calls unstructured and routes each element type into typed chunk lists.
Single responsibility: element routing only.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from .models import ImageChunk, PDFChunkResult, TableChunk, TextChunk
from .strategy import ChunkingStrategy, HiResStrategy

logger = logging.getLogger(__name__)


class PDFPartitioner:
    def __init__(self, strategy: ChunkingStrategy = None) -> None:
        self._strategy = strategy or HiResStrategy

    def partition(self, file_path: str, paper_name: Optional[str] = None) -> PDFChunkResult:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"PDF not found: {file_path}")

        if paper_name is None:
            paper_name = os.path.splitext(os.path.basename(file_path))[0]

        logger.info("📄 Partitioning: %s", file_path)

        raw = self._call_unstructured(file_path)
        result = PDFChunkResult(paper_name=paper_name)
        c = {"text": 0, "table": 0, "image": 0}   # counters

        for el in raw:
            el_type = type(el).__name__
            page    = getattr(el.metadata, "page_number", 0) or 0
            section = getattr(el.metadata, "section", None) or "Unknown"

            if "Table" in el_type:
                result.table_chunks.append(TableChunk(
                    text=el.text,
                    html=getattr(el.metadata, "text_as_html", None),
                    page_number=page,
                    chunk_index=c["table"],
                    paper_name=paper_name,
                    section=section,
                    metadata={"element_type": el_type},
                ))
                c["table"] += 1

            elif "CompositeElement" in el_type:
                result.text_chunks.append(TextChunk(
                    text=el.text,
                    section=section,
                    page_number=page,
                    chunk_index=c["text"],
                    paper_name=paper_name,
                    metadata={"element_type": el_type},
                ))
                parent_idx = c["text"]
                c["text"] += 1

                # Extract images embedded inside this composite element
                for sub in (getattr(el.metadata, "orig_elements", None) or []):
                    if "Image" in type(sub).__name__:
                        b64 = getattr(sub.metadata, "image_base64", None)
                        if b64:
                            result.image_chunks.append(ImageChunk(
                                image_b64=b64,
                                page_number=getattr(sub.metadata, "page_number", page) or page,
                                chunk_index=c["image"],
                                paper_name=paper_name,
                                section=section,
                                parent_chunk_index=parent_idx,
                            ))
                            c["image"] += 1

            elif "Image" in el_type:
                b64 = getattr(el.metadata, "image_base64", None)
                if b64:
                    result.image_chunks.append(ImageChunk(
                        image_b64=b64,
                        page_number=page,
                        chunk_index=c["image"],
                        paper_name=paper_name,
                        section=section,
                    ))
                    c["image"] += 1

        logger.info("✅ %s → text=%d | tables=%d | images=%d",
                    paper_name, len(result.text_chunks),
                    len(result.table_chunks), len(result.image_chunks))
        return result

    def _call_unstructured(self, file_path: str):
        try:
            from unstructured.partition.pdf import partition_pdf
        except ImportError as exc:
            raise ImportError(
                "Install unstructured: pip install 'unstructured[pdf]'"
            ) from exc
        return partition_pdf(filename=file_path, **self._strategy.to_kwargs())