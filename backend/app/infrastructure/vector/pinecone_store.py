"""Reserved Pinecone adapter — not required for local development."""

from __future__ import annotations

from app.domain.interfaces.services.vector_store import VectorRecord, VectorSearchHit


class PineconeVectorStore:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        _ = args, kwargs
        raise NotImplementedError(
            "Pinecone is not configured for this environment. "
            "Use VECTOR_STORE_PROVIDER=chroma (local file-backed store)."
        )

    @property
    def provider_name(self) -> str:
        return "pinecone"

    async def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    async def delete(self, ids: list[str]) -> None:
        raise NotImplementedError

    async def delete_by_document(self, *, company_id: int, document_id: int) -> int:
        raise NotImplementedError

    async def similarity_search(
        self,
        *,
        company_id: int,
        query_embedding: list[float],
        top_k: int,
        document_id: int | None = None,
    ) -> list[VectorSearchHit]:
        raise NotImplementedError

    async def health(self) -> bool:
        return False
