"""
Text chunker — split documents into overlapping chunks for embedding.

Default: 500 tokens per chunk, 50 token overlap.
Uses a simple whitespace tokenizer (1 token ≈ 1 word) to stay dependency-free
and fast on CPU.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from config import CHUNK_OVERLAP_TOKENS, CHUNK_SIZE_TOKENS

logger = logging.getLogger(__name__)

# Rough word tokenizer — sufficient for chunking (not NLP-grade)
_WORD_RE = re.compile(r"\S+")


@dataclass
class TextChunk:
    """A single chunk with its position metadata."""

    text: str
    chunk_index: int
    start_token: int
    end_token: int
    source_id: str = ""  # paper PMID / arXiv ID / filename


def chunk_text(
    text: str,
    source_id: str = "",
    chunk_size: int = CHUNK_SIZE_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
) -> list[TextChunk]:
    """
    Split *text* into overlapping chunks of approximately *chunk_size* words.

    Returns a list of ``TextChunk`` objects.
    """
    words = _WORD_RE.findall(text)
    if not words:
        return []

    chunks: list[TextChunk] = []
    start = 0
    idx = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append(
            TextChunk(
                text=" ".join(chunk_words),
                chunk_index=idx,
                start_token=start,
                end_token=end,
                source_id=source_id,
            )
        )
        idx += 1
        start += chunk_size - overlap

    logger.info(
        "Chunked '%s' → %d chunks (size=%d, overlap=%d)",
        source_id or "text",
        len(chunks),
        chunk_size,
        overlap,
    )
    return chunks
