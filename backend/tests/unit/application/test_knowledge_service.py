"""Unit tests for knowledge extract/chunk/embed/vector/retrieval rules."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.context import RequestActor
from app.application.dto.knowledge import KnowledgeSearchInput
from app.application.services.knowledge.knowledge_service import KnowledgeService
from app.domain.entities.document import Document
from app.domain.enums.document_status import DocumentStatus, StorageProvider
from app.domain.exceptions.knowledge import KnowledgeAccessDeniedError, KnowledgeValidationError
from app.infrastructure.knowledge.chunker import RecursiveCharacterChunker
from app.infrastructure.knowledge.document_processor import DefaultDocumentProcessor
from app.infrastructure.knowledge.embeddings.hashing import HashingEmbeddingProvider
from app.infrastructure.vector.local_store import LocalPersistentVectorStore


def test_chunker_overlap_order_and_nonempty() -> None:
    chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=5)
    text = "alpha beta gamma delta epsilon zeta eta theta"
    chunks = chunker.chunk(text)
    assert chunks
    assert all(c.content.strip() for c in chunks)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    if len(chunks) > 1:
        assert chunks[0].overlap_previous is False
        assert chunks[-1].overlap_next is False


def test_extractor_txt_md_and_unsupported() -> None:
    processor = DefaultDocumentProcessor()
    txt = processor.extract(b"hello world", filename="a.txt", mime_type="text/plain")
    assert "hello" in txt.text
    md = processor.extract(b"# Title\nbody", filename="a.md", mime_type="text/markdown")
    assert "Title" in md.text
    with pytest.raises(KnowledgeValidationError):
        processor.extract(b"MZ", filename="x.exe", mime_type="application/octet-stream")


@pytest.mark.asyncio
async def test_hashing_embed_and_local_vector_tenant_filter(tmp_path) -> None:
    embedder = HashingEmbeddingProvider(dimension=32)
    vectors = await embedder.embed_texts(["refund policy", "shipping policy"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 32

    store = LocalPersistentVectorStore(tmp_path)
    from app.domain.interfaces.services.vector_store import VectorRecord

    await store.upsert(
        [
            VectorRecord(
                id="a1",
                embedding=vectors[0],
                content="refund policy",
                metadata={"company_id": 1, "document_id": 10, "chunk_uuid": "a1"},
            ),
            VectorRecord(
                id="b1",
                embedding=vectors[1],
                content="shipping policy",
                metadata={"company_id": 2, "document_id": 20, "chunk_uuid": "b1"},
            ),
        ]
    )
    hits = await store.similarity_search(
        company_id=1,
        query_embedding=vectors[0],
        top_k=5,
    )
    assert hits
    assert all(int(h.metadata["company_id"]) == 1 for h in hits)
    assert all(int(h.metadata["document_id"]) != 20 for h in hits)


class _DocRepo:
    def __init__(self, docs: dict[int, Document]) -> None:
        self.docs = docs

    async def get_by_id(
        self, document_id: int, *, include_deleted: bool = False
    ) -> Document | None:
        doc = self.docs.get(document_id)
        if doc is None:
            return None
        if not include_deleted and doc.is_deleted:
            return None
        return doc

    async def update(self, document_id: int, data: dict[str, Any], **_: Any) -> Document | None:
        doc = self.docs[document_id]
        for key, value in data.items():
            object.__setattr__(doc, key, value)
        return doc


class _ChunkRepo:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    async def bulk_create(self, rows: list[dict[str, Any]]) -> list[Any]:
        self.rows.extend(rows)
        return []

    async def delete_by_document(self, document_id: int, *, company_id: int | None = None) -> int:
        before = len(self.rows)
        self.rows = [
            r
            for r in self.rows
            if not (
                r["document_id"] == document_id
                and (company_id is None or r["company_id"] == company_id)
            )
        ]
        return before - len(self.rows)

    async def get_by_uuid(self, chunk_uuid: str) -> Any:
        return None

    async def list_by_document(self, document_id: int, *, company_id: int | None = None) -> list:
        return []

    async def count_by_document(self, document_id: int, *, company_id: int | None = None) -> int:
        return 0


class _Storage:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    async def get(self, key: str) -> bytes:
        _ = key
        return self.payload

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        return key

    async def delete(self, key: str) -> None:
        return None

    async def exists(self, key: str) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "LOCAL"


class _Audit:
    async def log(self, **kwargs: Any) -> None:
        _ = kwargs


def _doc(company_id: int, document_id: int) -> Document:
    now = datetime.now(UTC)
    return Document(
        document_id=document_id,
        company_id=company_id,
        uploaded_by=1,
        document_name="Policy",
        original_filename="policy.txt",
        storage_path="companies/1/documents/x.txt",
        storage_provider=StorageProvider.LOCAL,
        mime_type="text/plain",
        file_extension=".txt",
        file_size_bytes=10,
        file_hash="abc",
        processing_status=DocumentStatus.QUEUED,
        language="en",
        version=1,
        total_chunks=0,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_search_rejects_cross_tenant_document_filter(tmp_path) -> None:
    doc_a = _doc(1, 10)
    doc_a.processing_status = DocumentStatus.COMPLETED
    service = KnowledgeService(
        documents=_DocRepo({10: doc_a}),
        chunks=_ChunkRepo(),
        storage=_Storage(b"hello"),
        processor=DefaultDocumentProcessor(),
        chunker=RecursiveCharacterChunker(chunk_size=50, chunk_overlap=5),
        embeddings=HashingEmbeddingProvider(dimension=16),
        vectors=LocalPersistentVectorStore(tmp_path),
        audit_logger=_Audit(),
    )
    actor_b = RequestActor(
        user_id=2,
        company_id=2,
        permissions=frozenset({"knowledge.search"}),
    )
    with pytest.raises(KnowledgeAccessDeniedError):
        await service.search(
            KnowledgeSearchInput(query="hello", document_id=10),
            actor_b,
        )
