"""
src/services/chunking/models.py
────────────────────────────────
Typed data containers for every chunk modality. No logic here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TextChunk:
    text: str
    section: str
    page_number: int
    chunk_index: int
    paper_name: Optional[str] = None
    section_id: Optional[str] = None
    section_level: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class TableChunk:
    text: str
    html: Optional[str]
    page_number: int
    chunk_index: int
    paper_name: Optional[str] = None
    section: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class ImageChunk:
    image_b64: str
    page_number: int
    chunk_index: int
    paper_name: Optional[str] = None
    section: Optional[str] = None
    parent_chunk_index: Optional[int] = None   # TextChunk this image came from
    metadata: Dict = field(default_factory=dict)


@dataclass
class PDFChunkResult:
    paper_name: str
    text_chunks: List[TextChunk] = field(default_factory=list)
    table_chunks: List[TableChunk] = field(default_factory=list)
    image_chunks: List[ImageChunk] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.text_chunks) + len(self.table_chunks) + len(self.image_chunks)

    def __repr__(self) -> str:
        return (
            f"PDFChunkResult(paper={self.paper_name!r}, "
            f"text={len(self.text_chunks)}, "
            f"tables={len(self.table_chunks)}, "
            f"images={len(self.image_chunks)}, "
            f"total={self.total})"
        )