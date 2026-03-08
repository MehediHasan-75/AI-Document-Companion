"""
src/services/chunking/strategy.py
───────────────────────────────────
Unstructured partition_pdf parameters as swappable config objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ChunkingStrategy:
    """All params forwarded to unstructured's partition_pdf."""
    strategy: str = "hi_res"
    chunking_strategy: str = "by_title"
    max_characters: int = 10_000
    combine_text_under_n_chars: int = 2_000
    new_after_n_chars: int = 6_000
    infer_table_structure: bool = True
    extract_image_block_types: List[str] = field(default_factory=lambda: ["Image"])

    def to_kwargs(self) -> dict:
        return {
            "strategy": self.strategy,
            "chunking_strategy": self.chunking_strategy,
            "max_characters": self.max_characters,
            "combine_text_under_n_chars": self.combine_text_under_n_chars,
            "new_after_n_chars": self.new_after_n_chars,
            "infer_table_structure": self.infer_table_structure,
            "extract_image_block_types": self.extract_image_block_types,
            "extract_image_block_to_payload": True,  # always base64
        }


# ── Pre-built strategies ────────────────────────────────────────────────────────

#: Full fidelity — tables + images, slower
HiResStrategy = ChunkingStrategy()

#: Fast pass — text only, no tables/images
FastStrategy = ChunkingStrategy(
    strategy="fast",
    infer_table_structure=False,
    extract_image_block_types=[],
    max_characters=5_000,
    combine_text_under_n_chars=500,
    new_after_n_chars=3_000,
)