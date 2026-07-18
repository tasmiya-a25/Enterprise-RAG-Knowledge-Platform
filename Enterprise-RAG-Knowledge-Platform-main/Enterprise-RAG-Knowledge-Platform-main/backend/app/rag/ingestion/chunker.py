"""
Chunking strategies.

`recursive_chunk` is the default and handles the general case: it tries
to split on paragraph -> sentence -> word boundaries, in that order,
so chunks stay semantically coherent instead of cutting mid-sentence.

`markdown_chunk` additionally respects markdown headers as split points,
which keeps a section's content together.
"""
import re

from app.config.settings import get_settings

settings = get_settings()

_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split_text(text: str, separators: list[str], chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    if not separators:
        # Fallback: hard character split
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]

    sep, *rest = separators
    parts = text.split(sep)
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = (current + sep + part) if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part) > chunk_size:
                chunks.extend(_split_text(part, rest, chunk_size, overlap))
                current = ""
            else:
                current = part

    if current:
        chunks.append(current)

    # Apply overlap by prepending the tail of the previous chunk
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for prev, curr in zip(chunks, chunks[1:]):
            tail = prev[-overlap:]
            overlapped.append(tail + curr)
        return overlapped

    return chunks


def recursive_chunk(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap if overlap is not None else settings.CHUNK_OVERLAP
    return [c.strip() for c in _split_text(text, _SEPARATORS, chunk_size, overlap) if c.strip()]


def markdown_chunk(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """Split first on markdown headers, then recursively chunk each section."""
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap if overlap is not None else settings.CHUNK_OVERLAP

    sections = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    chunks: list[str] = []
    for section in sections:
        if not section.strip():
            continue
        chunks.extend(recursive_chunk(section, chunk_size, overlap))
    return chunks


def sliding_window_chunk(text: str, window: int | None = None, stride: int | None = None) -> list[str]:
    """Fixed-size character windows with a configurable stride (window - overlap)."""
    window = window or settings.CHUNK_SIZE
    stride = stride or max(window - settings.CHUNK_OVERLAP, 1)
    return [text[i:i + window].strip() for i in range(0, len(text), stride) if text[i:i + window].strip()]


CHUNKERS = {
    "recursive": recursive_chunk,
    "markdown": markdown_chunk,
    "sliding_window": sliding_window_chunk,
}


def chunk_text(text: str, strategy: str = "recursive") -> list[str]:
    fn = CHUNKERS.get(strategy, recursive_chunk)
    return fn(text)
