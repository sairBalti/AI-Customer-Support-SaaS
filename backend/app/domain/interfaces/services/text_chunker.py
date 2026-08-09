"""Text chunking port."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class TextChunk:
    """A single ordered chunk of source text."""

    index: int
    content: str
    page_number: int | None = None
    overlap_previous: bool = False
    overlap_next: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class TextChunker(Protocol):
    def chunk(
        self,
        text: str,
        *,
        page_texts: tuple[str, ...] = (),
    ) -> list[TextChunk]: ...
