"""Markdown text extractor."""

from __future__ import annotations

from app.domain.interfaces.services.text_extractor import ExtractedDocument


class MarkdownExtractor:
    supported_extensions = frozenset({".md", ".markdown"})
    supported_mime_types = frozenset({"text/markdown", "text/x-markdown", "text/plain"})

    def extract(self, data: bytes, *, filename: str, mime_type: str) -> ExtractedDocument:
        _ = filename, mime_type
        text = data.decode("utf-8", errors="replace").strip()
        return ExtractedDocument(text=text, page_texts=(text,) if text else ())
