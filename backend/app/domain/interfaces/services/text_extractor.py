"""Text extraction port — convert document bytes to plain text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class ExtractedDocument:
    """Normalized extraction result."""

    text: str
    page_texts: tuple[str, ...] = ()
    metadata: dict[str, object] | None = None


@runtime_checkable
class TextExtractor(Protocol):
    """Extract plain text from a specific content type."""

    @property
    def supported_extensions(self) -> frozenset[str]: ...

    @property
    def supported_mime_types(self) -> frozenset[str]: ...

    def extract(self, data: bytes, *, filename: str, mime_type: str) -> ExtractedDocument: ...


@runtime_checkable
class DocumentProcessor(Protocol):
    """Registry that routes bytes to the correct TextExtractor."""

    def extract(self, data: bytes, *, filename: str, mime_type: str) -> ExtractedDocument: ...
