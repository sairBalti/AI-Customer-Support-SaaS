"""Knowledge indexing / retrieval application service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.application.context import RequestActor
from app.application.dto.knowledge import KnowledgeSearchInput
from app.core.security.rbac import ensure_permissions
from app.domain.entities.document import Document
from app.domain.entities.knowledge_chunk import RetrievedChunk
from app.domain.enums.document_status import DocumentStatus
from app.domain.exceptions.document import DocumentNotFoundError
from app.domain.exceptions.knowledge import (
    KnowledgeAccessDeniedError,
    KnowledgeProcessingError,
    KnowledgeValidationError,
)
from app.domain.interfaces.repositories.document_repository import DocumentRepository
from app.domain.interfaces.repositories.knowledge_chunk_repository import (
    KnowledgeChunkRepository,
)
from app.domain.interfaces.services.audit_logger import AuditLogger
from app.domain.interfaces.services.embedding_service import EmbeddingProvider
from app.domain.interfaces.services.object_storage import ObjectStorage
from app.domain.interfaces.services.text_chunker import TextChunker
from app.domain.interfaces.services.text_extractor import DocumentProcessor
from app.domain.interfaces.services.vector_store import VectorRecord, VectorStore


class KnowledgeService:
    """Orchestrates extract → chunk → embed → vector upsert → relational metadata."""

    def __init__(
        self,
        *,
        documents: DocumentRepository,
        chunks: KnowledgeChunkRepository,
        storage: ObjectStorage,
        processor: DocumentProcessor,
        chunker: TextChunker,
        embeddings: EmbeddingProvider,
        vectors: VectorStore,
        audit_logger: AuditLogger,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._storage = storage
        self._processor = processor
        self._chunker = chunker
        self._embeddings = embeddings
        self._vectors = vectors
        self._audit = audit_logger
        self._pending_audits: list[dict[str, Any]] = []

    async def flush_audits(self) -> None:
        events = list(self._pending_audits)
        self._pending_audits.clear()
        for event in events:
            await self._audit.log(**event)

    def discard_audits(self) -> None:
        self._pending_audits.clear()

    async def process_document(self, document_id: int, actor: RequestActor) -> Document:
        ensure_permissions(actor, "knowledge.process")
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        self._assert_tenant_access(document.company_id, actor)
        return await self._run_pipeline(document, actor, action="knowledge.process")

    async def reindex_document(self, document_id: int, actor: RequestActor) -> Document:
        """Idempotent reindex: clear prior index then re-run the pipeline."""
        # Accept either knowledge.process or documents.reindex
        if not (
            actor.has_permission("knowledge.process") or actor.has_permission("documents.reindex")
        ):
            from app.domain.exceptions.auth import InsufficientPermissionError

            raise InsufficientPermissionError(
                "Missing permission(s): knowledge.process or documents.reindex",
            )
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        self._assert_tenant_access(document.company_id, actor)
        return await self._run_pipeline(document, actor, action="knowledge.reindex")

    async def deindex_document(
        self,
        document_id: int,
        company_id: int,
        actor: RequestActor | None = None,
    ) -> None:
        """Remove relational chunks + vectors (used on soft-delete)."""
        if actor is not None:
            self._assert_tenant_access(company_id, actor)
        await self._vectors.delete_by_document(company_id=company_id, document_id=document_id)
        await self._chunks.delete_by_document(document_id, company_id=company_id)
        self._queue_audit(
            action="knowledge.deindex",
            entity_id=document_id,
            company_id=company_id,
            user_id=actor.user_id if actor else None,
        )

    async def search(
        self,
        data: KnowledgeSearchInput,
        actor: RequestActor,
    ) -> list[RetrievedChunk]:
        ensure_permissions(actor, "knowledge.search")
        query = (data.query or "").strip()
        if not query:
            raise KnowledgeValidationError("query is required.")
        top_k = data.top_k if data.top_k > 0 else 5
        company_id = self._resolve_company_id(data.company_id, actor)

        if data.document_id is not None:
            document = await self._documents.get_by_id(data.document_id)
            if document is None or document.company_id != company_id:
                raise KnowledgeAccessDeniedError(
                    "Cannot search knowledge for another company document.",
                )
            if document.is_deleted or document.processing_status != DocumentStatus.COMPLETED:
                return []

        query_vectors = await self._embeddings.embed_texts([query])
        hits = await self._vectors.similarity_search(
            company_id=company_id,
            query_embedding=query_vectors[0],
            top_k=top_k,
            document_id=data.document_id,
        )

        results: list[RetrievedChunk] = []
        for hit in hits:
            meta = hit.metadata or {}
            # Defense in depth — never return another tenant's vectors.
            if int(meta.get("company_id", -1)) != int(company_id):
                continue
            doc_id = int(meta.get("document_id", 0))
            document = await self._documents.get_by_id(doc_id)
            if (
                document is None
                or document.is_deleted
                or document.processing_status != DocumentStatus.COMPLETED
                or document.company_id != company_id
            ):
                continue
            chunk = await self._chunks.get_by_uuid(str(meta.get("chunk_uuid") or hit.id))
            results.append(
                RetrievedChunk(
                    document_id=doc_id,
                    chunk_id=chunk.chunk_id if chunk else None,
                    chunk_uuid=str(meta.get("chunk_uuid") or hit.id),
                    content=hit.content,
                    score=float(hit.score),
                    company_id=company_id,
                    chunk_index=int(meta.get("chunk_index", 0)),
                    metadata=dict(meta),
                    source_filename=str(meta.get("source_filename") or "") or None,
                    page_number=(
                        int(meta["page_number"]) if meta.get("page_number") is not None else None
                    ),
                )
            )
        self._queue_audit(
            action="knowledge.search",
            entity_id=company_id,
            company_id=company_id,
            user_id=actor.user_id,
            metadata={"top_k": top_k, "hits": len(results), "document_id": data.document_id},
        )
        return results

    async def _run_pipeline(
        self,
        document: Document,
        actor: RequestActor,
        *,
        action: str,
    ) -> Document:
        now = datetime.now(UTC)
        await self._documents.update(
            document.document_id,
            {
                "processing_status": DocumentStatus.PROCESSING,
                "processing_started_at": now,
                "failure_reason": None,
                "updated_at": now,
            },
        )
        try:
            # Clear previous index (idempotent reindex / reprocess).
            await self._vectors.delete_by_document(
                company_id=document.company_id,
                document_id=document.document_id,
            )
            await self._chunks.delete_by_document(
                document.document_id,
                company_id=document.company_id,
            )

            raw = await self._storage.get(document.storage_path)
            await self._set_status(document.document_id, DocumentStatus.CHUNKING)
            extracted = self._processor.extract(
                raw,
                filename=document.original_filename,
                mime_type=document.mime_type,
            )
            text_chunks = self._chunker.chunk(
                extracted.text,
                page_texts=extracted.page_texts,
            )
            if not text_chunks:
                raise KnowledgeProcessingError("Chunking produced no content.")

            await self._set_status(document.document_id, DocumentStatus.EMBEDDING)
            embeddings = await self._embeddings.embed_texts([c.content for c in text_chunks])
            if len(embeddings) != len(text_chunks):
                raise KnowledgeProcessingError("Embedding provider returned unexpected size.")

            await self._set_status(document.document_id, DocumentStatus.INDEXING)
            rows: list[dict[str, Any]] = []
            records: list[VectorRecord] = []
            stamp = datetime.now(UTC)
            for chunk, vector in zip(text_chunks, embeddings, strict=True):
                chunk_uuid = str(uuid.uuid4())
                embedding_id = f"doc-{document.document_id}-chunk-{chunk.index}-{chunk_uuid}"
                meta = {
                    "company_id": document.company_id,
                    "document_id": document.document_id,
                    "chunk_index": chunk.index,
                    "chunk_uuid": chunk_uuid,
                    "source_filename": document.original_filename,
                    "page_number": chunk.page_number,
                    "mime_type": document.mime_type,
                }
                rows.append(
                    {
                        "company_id": document.company_id,
                        "document_id": document.document_id,
                        "chunk_number": chunk.index,
                        "chunk_uuid": chunk_uuid,
                        "embedding_id": embedding_id,
                        "chunk_text": chunk.content,
                        "token_count": max(len(chunk.content.split()), 1),
                        "character_count": len(chunk.content),
                        "page_number": chunk.page_number,
                        "overlap_previous": chunk.overlap_previous,
                        "overlap_next": chunk.overlap_next,
                        "embedding_provider": self._embeddings.provider_name,
                        "embedding_model": self._embeddings.model_name,
                        "embedding_dimension": self._embeddings.dimension,
                        "language": document.language,
                        "version": 1,
                        "retrieval_count": 0,
                        "chunk_metadata": meta,
                        "created_at": stamp,
                        "updated_at": stamp,
                    }
                )
                records.append(
                    VectorRecord(
                        id=chunk_uuid,
                        embedding=vector,
                        content=chunk.content,
                        metadata=meta,
                    )
                )

            await self._vectors.upsert(records)
            created = await self._chunks.bulk_create(rows)
            completed_at = datetime.now(UTC)
            updated = await self._documents.update(
                document.document_id,
                {
                    "processing_status": DocumentStatus.COMPLETED,
                    "processing_completed_at": completed_at,
                    "indexed_at": completed_at,
                    "total_chunks": len(created),
                    "embedding_provider": self._embeddings.provider_name,
                    "embedding_model": self._embeddings.model_name,
                    "failure_reason": None,
                    "updated_at": completed_at,
                },
            )
            if updated is None:
                raise DocumentNotFoundError()
            self._queue_audit(
                action=action,
                entity_id=document.document_id,
                company_id=document.company_id,
                user_id=actor.user_id,
                metadata={"chunks": len(created), "vector_provider": self._vectors.provider_name},
            )
            return updated
        except Exception as exc:
            await self._documents.update(
                document.document_id,
                {
                    "processing_status": DocumentStatus.FAILED,
                    "failure_reason": str(exc)[:2000],
                    "updated_at": datetime.now(UTC),
                },
            )
            if isinstance(exc, (KnowledgeValidationError, KnowledgeProcessingError)):
                raise
            raise KnowledgeProcessingError(str(exc)) from exc

    async def _set_status(self, document_id: int, status: DocumentStatus) -> None:
        await self._documents.update(
            document_id,
            {"processing_status": status, "updated_at": datetime.now(UTC)},
        )

    def _resolve_company_id(self, company_id: int | None, actor: RequestActor) -> int:
        if actor.is_super_admin:
            if company_id is not None:
                return int(company_id)
            if actor.company_id is None:
                raise KnowledgeValidationError("company_id is required.")
            return int(actor.company_id)
        if actor.company_id is None:
            raise KnowledgeAccessDeniedError("Authenticated user has no company.")
        if company_id is not None and int(company_id) != int(actor.company_id):
            raise KnowledgeAccessDeniedError(
                "Cannot access knowledge for another company.",
            )
        return int(actor.company_id)

    def _assert_tenant_access(self, company_id: int, actor: RequestActor) -> None:
        if actor.is_super_admin:
            return
        if actor.company_id is None or int(actor.company_id) != int(company_id):
            raise KnowledgeAccessDeniedError(
                "Cannot access knowledge for another company.",
            )

    def _queue_audit(
        self,
        *,
        action: str,
        entity_id: int,
        company_id: int | None,
        user_id: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._pending_audits.append(
            {
                "action": action,
                "entity": "knowledge",
                "entity_id": entity_id,
                "company_id": company_id,
                "user_id": user_id,
                "metadata": metadata or {},
            }
        )
