"""Knowledge chunk domain entity (MySQL metadata — vectors live in the vector store)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class KnowledgeChunk:
    chunk_id: int
    company_id: int
    document_id: int
    chunk_number: int
    chunk_uuid: str
    embedding_id: str
    chunk_text: str
    token_count: int
    character_count: int
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    language: str
    version: int
    retrieval_count: int
    created_at: datetime
    updated_at: datetime
    page_number: int | None = None
    section_title: str | None = None
    overlap_previous: bool = False
    overlap_next: bool = False
    last_retrieved_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievedChunk:
    """Ranked retrieval hit returned to the application layer."""

    document_id: int
    chunk_id: int | None
    chunk_uuid: str
    content: str
    score: float
    company_id: int
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    source_filename: str | None = None
    page_number: int | None = None
