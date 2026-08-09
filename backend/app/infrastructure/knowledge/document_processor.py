"""Document processor — routes bytes to the correct text extractor."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.domain.exceptions.knowledge import KnowledgeValidationError
from app.domain.interfaces.services.text_extractor import ExtractedDocument, TextExtractor
from app.infrastructure.knowledge.extractors.markdown import MarkdownExtractor
from app.infrastructure.knowledge.extractors.pdf_extractor import PdfExtractor
from app.infrastructure.knowledge.extractors.plain_text import PlainTextExtractor


class DefaultDocumentProcessor:
    """Local/dev document processor for PDF, TXT, and Markdown."""

    def __init__(self, extractors: list[TextExtractor] | None = None) -> None:
        self._extractors = extractors or [
            PdfExtractor(),
            PlainTextExtractor(),
            MarkdownExtractor(),
        ]

    def extract(self, data: bytes, *, filename: str, mime_type: str) -> ExtractedDocument:
        if not data:
            raise KnowledgeValidationError("Document content is empty.")
        ext = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
        mime = (mime_type or "").split(";")[0].strip().lower()

        extractor = None
        for candidate in self._extractors:
            if ext and ext in candidate.supported_extensions:
                extractor = candidate
                break
        if extractor is None:
            for candidate in self._extractors:
                if mime and mime in candidate.supported_mime_types:
                    extractor = candidate
                    break
        if extractor is None:
            raise KnowledgeValidationError(
                f"Unsupported file type for knowledge processing: {ext or mime or 'unknown'}."
            )

        result = extractor.extract(data, filename=filename, mime_type=mime_type)
        if not result.text.strip():
            raise KnowledgeValidationError(
                "No extractable text found in the document.",
            )
        return result
