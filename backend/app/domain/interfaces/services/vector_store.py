"""Vector store port (Chroma / Pinecone / local file)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class VectorRecord:
    """Unit stored in the vector database."""

    id: str
    embedding: list[float]
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VectorSearchHit:
    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VectorStore(Protocol):
    """Provider-agnostic vector persistence and similarity search."""

    @property
    def provider_name(self) -> str: ...

    async def upsert(self, records: list[VectorRecord]) -> None: ...

    async def delete(self, ids: list[str]) -> None: ...

    async def delete_by_document(self, *, company_id: int, document_id: int) -> int:
        """Delete all vectors for a tenant document. Returns deleted count."""
        ...

    async def similarity_search(
        self,
        *,
        company_id: int,
        query_embedding: list[float],
        top_k: int,
        document_id: int | None = None,
    ) -> list[VectorSearchHit]:
        """Search within a single company (tenant isolation is mandatory)."""
        ...

    async def health(self) -> bool: ...
