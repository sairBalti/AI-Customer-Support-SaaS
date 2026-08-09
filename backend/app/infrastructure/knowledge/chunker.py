"""Deterministic overlapping character chunker."""

from __future__ import annotations

from app.domain.interfaces.services.text_chunker import TextChunk


class RecursiveCharacterChunker:
    """Split text into ordered chunks with configurable size and overlap."""

    def __init__(self, *, chunk_size: int = 800, chunk_overlap: int = 100) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and < chunk_size")
        self._size = chunk_size
        self._overlap = chunk_overlap

    def chunk(
        self,
        text: str,
        *,
        page_texts: tuple[str, ...] = (),
    ) -> list[TextChunk]:
        if page_texts:
            return self._chunk_pages(page_texts)
        return self._chunk_flat(text.strip(), page_number=None)

    def _chunk_pages(self, page_texts: tuple[str, ...]) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        for page_idx, page_text in enumerate(page_texts, start=1):
            page_chunks = self._chunk_flat(page_text.strip(), page_number=page_idx)
            for item in page_chunks:
                item.index = len(chunks)
                chunks.append(item)
        return chunks

    def _chunk_flat(self, text: str, *, page_number: int | None) -> list[TextChunk]:
        if not text:
            return []
        if len(text) <= self._size:
            return [
                TextChunk(
                    index=0,
                    content=text,
                    page_number=page_number,
                    overlap_previous=False,
                    overlap_next=False,
                )
            ]

        chunks: list[TextChunk] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + self._size, length)
            if end < length:
                # Prefer splitting on whitespace near the window end.
                split_at = text.rfind(" ", start, end)
                if split_at > start + self._size // 4:
                    end = split_at
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    TextChunk(
                        index=len(chunks),
                        content=piece,
                        page_number=page_number,
                        overlap_previous=start > 0 and self._overlap > 0,
                        overlap_next=end < length and self._overlap > 0,
                    )
                )
            if end >= length:
                break
            next_start = max(end - self._overlap, start + 1)
            if next_start <= start:
                next_start = end
            start = next_start

        if chunks:
            chunks[0].overlap_previous = False
            chunks[-1].overlap_next = False
        return chunks
