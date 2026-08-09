"""PDF text extractor (pypdf)."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.domain.exceptions.knowledge import KnowledgeValidationError
from app.domain.interfaces.services.text_extractor import ExtractedDocument


class PdfExtractor:
    supported_extensions = frozenset({".pdf"})
    supported_mime_types = frozenset({"application/pdf", "application/octet-stream"})

    def extract(self, data: bytes, *, filename: str, mime_type: str) -> ExtractedDocument:
        _ = filename, mime_type
        try:
            reader = PdfReader(BytesIO(data))
        except Exception as exc:  # noqa: BLE001 — surface as domain validation
            raise KnowledgeValidationError(f"Unable to read PDF: {exc}") from exc

        pages: list[str] = []
        for page in reader.pages:
            try:
                page_text = (page.extract_text() or "").strip()
            except Exception:  # noqa: BLE001
                page_text = ""
            if page_text:
                pages.append(page_text)

        text = "\n\n".join(pages).strip()
        return ExtractedDocument(text=text, page_texts=tuple(pages))
