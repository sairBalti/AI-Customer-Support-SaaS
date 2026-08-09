"""Knowledge / RAG application DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class KnowledgeSearchInput:
    query: str
    top_k: int = 5
    document_id: int | None = None
    company_id: int | None = None
