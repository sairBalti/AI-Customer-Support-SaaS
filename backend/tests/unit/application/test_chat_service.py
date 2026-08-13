"""Unit tests for chat RAG agent (fake LLM, no paid APIs)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.context import RequestActor
from app.application.dto.chat import CreateConversationInput, SendChatMessageInput
from app.application.services.chat.chat_service import ChatService
from app.application.services.chat.prompts import (
    NO_CONTEXT_ANSWER,
    citations_from_chunks,
    format_retrieval_context,
)
from app.domain.entities.document import Document
from app.domain.entities.knowledge_chunk import RetrievedChunk
from app.domain.enums.document_status import DocumentStatus, StorageProvider
from app.domain.exceptions.chat import ChatAccessDeniedError, ChatNotFoundError, ChatValidationError
from app.domain.interfaces.services.vector_store import VectorRecord
from app.infrastructure.knowledge.embeddings.hashing import HashingEmbeddingProvider
from app.infrastructure.llm.fake_client import FakeLlmClient
from app.infrastructure.vector.local_store import LocalPersistentVectorStore


def test_prompt_formatting_and_citations() -> None:
    chunks = [
        RetrievedChunk(
            document_id=1,
            chunk_id=10,
            chunk_uuid="c1",
            content="Refunds within 30 days",
            score=0.9,
            company_id=1,
            chunk_index=0,
            source_filename="refund.txt",
            page_number=2,
        )
    ]
    assert "Refunds" in format_retrieval_context(chunks)
    cites = citations_from_chunks(chunks, document_names={1: "Refund Policy"})
    assert cites[0]["document_name"] == "Refund Policy"
    assert cites[0]["page"] == 2


@pytest.mark.asyncio
async def test_fake_llm_grounded_and_empty_context() -> None:
    llm = FakeLlmClient()
    empty = await llm.generate_response(
        system_prompt="sys",
        user_message="hello",
        context="",
    )
    assert "knowledge base" in empty.content.lower()
    grounded = await llm.generate_response(
        system_prompt="sys",
        user_message="refund?",
        context="Policy allows returns in 30 days.",
    )
    assert "30 days" in grounded.content


class _SessionRepo:
    def __init__(self) -> None:
        self.rows: dict[int, Any] = {}
        self._next = 1

    async def create(self, data: dict[str, Any]) -> Any:
        from app.domain.entities.chat_session import ChatSession
        from app.domain.enums.chat_status import ChatSessionStatus

        sid = self._next
        self._next += 1
        session = ChatSession(
            session_id=sid,
            company_id=int(data["company_id"]),
            customer_id=int(data["customer_id"]),
            session_uuid=data["session_uuid"],
            title=data.get("title"),
            language=data.get("language", "en"),
            ai_provider=data["ai_provider"],
            ai_model=data["ai_model"],
            session_status=data["session_status"],
            total_messages=0,
            total_prompt_tokens=0,
            total_completion_tokens=0,
            total_tokens=0,
            estimated_cost=data["estimated_cost"],
            escalation_required=False,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            metadata={},
        )
        if isinstance(session.session_status, ChatSessionStatus):
            pass
        self.rows[sid] = session
        return session

    async def get_by_id(self, session_id: int, *, company_id: int | None = None) -> Any:
        session = self.rows.get(session_id)
        if session is None:
            return None
        if company_id is not None and session.company_id != company_id:
            return None
        return session

    async def list_by_company(
        self,
        company_id: int,
        *,
        customer_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        items = [s for s in self.rows.values() if s.company_id == company_id]
        if customer_id is not None:
            items = [s for s in items if s.customer_id == customer_id]
        return items[offset : offset + limit]

    async def update(
        self,
        session_id: int,
        data: dict[str, Any],
        *,
        company_id: int | None = None,
    ) -> Any:
        session = await self.get_by_id(session_id, company_id=company_id)
        if session is None:
            return None
        for key, value in data.items():
            object.__setattr__(session, key, value)
        return session

    async def delete_by_id(
        self,
        session_id: int,
        *,
        company_id: int | None = None,
    ) -> bool:
        session = await self.get_by_id(session_id, company_id=company_id)
        if session is None:
            return False
        del self.rows[session_id]
        return True

    async def delete_by_company(
        self,
        company_id: int,
        *,
        customer_id: int | None = None,
    ) -> int:
        to_delete = [
            sid
            for sid, session in self.rows.items()
            if session.company_id == company_id
            and (customer_id is None or session.customer_id == customer_id)
        ]
        for sid in to_delete:
            del self.rows[sid]
        return len(to_delete)


class _MessageRepo:
    def __init__(self) -> None:
        self.rows: list[Any] = []
        self._next = 1

    async def create(self, data: dict[str, Any]) -> Any:
        from decimal import Decimal

        from app.domain.entities.chat_message import ChatMessage

        msg = ChatMessage(
            message_id=self._next,
            session_id=int(data["session_id"]),
            company_id=int(data["company_id"]),
            message_uuid=data["message_uuid"],
            message_type=data["message_type"],
            sender_type=data["sender_type"],
            message_text=data["message_text"],
            prompt_tokens=int(data.get("prompt_tokens", 0)),
            completion_tokens=int(data.get("completion_tokens", 0)),
            total_tokens=int(data.get("total_tokens", 0)),
            estimated_cost=Decimal(data.get("estimated_cost", 0)),
            is_escalated=False,
            created_at=data["created_at"],
            sender_id=data.get("sender_id"),
            parent_message_id=data.get("parent_message_id"),
            ai_model=data.get("ai_model"),
            ai_provider=data.get("ai_provider"),
            response_time_ms=data.get("response_time_ms"),
            retrieved_chunks=list(data.get("retrieved_chunks") or []),
            citations=list(data.get("citations") or []),
            metadata=dict(data.get("metadata") or {}),
        )
        self._next += 1
        self.rows.append(msg)
        return msg

    async def list_by_session(
        self,
        session_id: int,
        *,
        company_id: int | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Any]:
        items = [m for m in self.rows if m.session_id == session_id]
        if company_id is not None:
            items = [m for m in items if m.company_id == company_id]
        return items[offset : offset + limit]

    async def get_by_id(self, message_id: int, *, company_id: int | None = None) -> Any:
        for msg in self.rows:
            if msg.message_id == message_id and (
                company_id is None or msg.company_id == company_id
            ):
                return msg
        return None

    async def delete_by_session(
        self,
        session_id: int,
        *,
        company_id: int | None = None,
    ) -> int:
        kept = []
        removed = 0
        for msg in self.rows:
            if msg.session_id != session_id:
                kept.append(msg)
                continue
            if company_id is not None and msg.company_id != company_id:
                kept.append(msg)
                continue
            removed += 1
        self.rows = kept
        return removed


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


class _Audit:
    async def log(self, **kwargs: Any) -> None:
        _ = kwargs


def _doc(company_id: int, document_id: int) -> Document:
    now = datetime.now(UTC)
    return Document(
        document_id=document_id,
        company_id=company_id,
        uploaded_by=1,
        document_name="Refund Policy",
        original_filename="refund.txt",
        storage_path="x",
        storage_provider=StorageProvider.LOCAL,
        mime_type="text/plain",
        file_extension=".txt",
        file_size_bytes=10,
        file_hash="abc",
        processing_status=DocumentStatus.COMPLETED,
        language="en",
        version=1,
        total_chunks=1,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_chat_no_context_fallback_and_tenant_guard(tmp_path) -> None:
    service = ChatService(
        sessions=_SessionRepo(),
        messages=_MessageRepo(),
        documents=_DocRepo({}),
        embeddings=HashingEmbeddingProvider(dimension=16),
        vectors=LocalPersistentVectorStore(tmp_path),
        llm=FakeLlmClient(),
        audit_logger=_Audit(),
        top_k=3,
    )
    actor = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"chat.start", "chat.read"}),
    )
    conversation = await service.create_conversation(CreateConversationInput(), actor)
    result = await service.send_message(
        conversation.session_id,
        SendChatMessageInput(content="Do you offer refunds?"),
        actor,
    )
    assert result.used_knowledge is False
    assert result.answer == NO_CONTEXT_ANSWER
    assert result.sources == []

    outsider = RequestActor(
        user_id=9,
        company_id=2,
        role_name="CUSTOMER",
        permissions=frozenset({"chat.start", "chat.read"}),
    )
    with pytest.raises(ChatAccessDeniedError):
        await service.get_conversation(conversation.session_id, outsider)


@pytest.mark.asyncio
async def test_chat_rag_with_sources(tmp_path) -> None:
    embeddings = HashingEmbeddingProvider(dimension=32)
    store = LocalPersistentVectorStore(tmp_path)
    vector = (await embeddings.embed_texts(["refund policy allows returns within thirty days"]))[0]
    await store.upsert(
        [
            VectorRecord(
                id="c1",
                embedding=vector,
                content="Refund policy allows returns within thirty days.",
                metadata={
                    "company_id": 1,
                    "document_id": 10,
                    "chunk_uuid": "c1",
                    "chunk_index": 0,
                    "source_filename": "refund.txt",
                    "page_number": 1,
                },
            )
        ]
    )
    service = ChatService(
        sessions=_SessionRepo(),
        messages=_MessageRepo(),
        documents=_DocRepo({10: _doc(1, 10)}),
        embeddings=embeddings,
        vectors=store,
        llm=FakeLlmClient(),
        audit_logger=_Audit(),
        top_k=3,
    )
    actor = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"chat.start", "chat.read"}),
    )
    conversation = await service.create_conversation(
        CreateConversationInput(title="Help"),
        actor,
    )
    result = await service.send_message(
        conversation.session_id,
        SendChatMessageInput(content="What is the refund policy?"),
        actor,
    )
    assert result.used_knowledge is True
    assert result.sources
    assert result.sources[0]["document_id"] == 10
    assert "thirty days" in result.answer.lower() or "Refund" in result.answer


@pytest.mark.asyncio
async def test_chat_requires_company_context() -> None:
    service = ChatService(
        sessions=_SessionRepo(),
        messages=_MessageRepo(),
        documents=_DocRepo({}),
        embeddings=HashingEmbeddingProvider(dimension=8),
        vectors=LocalPersistentVectorStore("."),
        llm=FakeLlmClient(),
        audit_logger=_Audit(),
    )
    actor = RequestActor(
        user_id=1,
        company_id=None,
        permissions=frozenset({"chat.start"}),
    )
    with pytest.raises(ChatValidationError):
        await service.create_conversation(CreateConversationInput(), actor)


@pytest.mark.asyncio
async def test_delete_conversation_scoped_to_customer() -> None:
    sessions = _SessionRepo()
    service = ChatService(
        sessions=sessions,
        messages=_MessageRepo(),
        documents=_DocRepo({}),
        embeddings=HashingEmbeddingProvider(dimension=8),
        vectors=LocalPersistentVectorStore("."),
        llm=FakeLlmClient(),
        audit_logger=_Audit(),
    )
    owner = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"chat.start", "chat.read"}),
    )
    other = RequestActor(
        user_id=2,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"chat.start", "chat.read"}),
    )
    conversation = await service.create_conversation(CreateConversationInput(), owner)
    with pytest.raises(ChatAccessDeniedError):
        await service.delete_conversation(conversation.session_id, other)
    await service.delete_conversation(conversation.session_id, owner)
    with pytest.raises(ChatNotFoundError):
        await service.get_conversation(conversation.session_id, owner)


@pytest.mark.asyncio
async def test_delete_conversation_after_messages(tmp_path) -> None:
    service = ChatService(
        sessions=_SessionRepo(),
        messages=_MessageRepo(),
        documents=_DocRepo({}),
        embeddings=HashingEmbeddingProvider(dimension=16),
        vectors=LocalPersistentVectorStore(tmp_path),
        llm=FakeLlmClient(),
        audit_logger=_Audit(),
    )
    actor = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"chat.start", "chat.read"}),
    )
    conversation = await service.create_conversation(CreateConversationInput(), actor)
    await service.send_message(
        conversation.session_id,
        SendChatMessageInput(content="Need help with billing"),
        actor,
    )
    await service.delete_conversation(conversation.session_id, actor)
    with pytest.raises(ChatNotFoundError):
        await service.get_conversation(conversation.session_id, actor)


@pytest.mark.asyncio
async def test_delete_all_conversations_for_customer_only() -> None:
    sessions = _SessionRepo()
    service = ChatService(
        sessions=sessions,
        messages=_MessageRepo(),
        documents=_DocRepo({}),
        embeddings=HashingEmbeddingProvider(dimension=8),
        vectors=LocalPersistentVectorStore("."),
        llm=FakeLlmClient(),
        audit_logger=_Audit(),
    )
    owner = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"chat.start", "chat.read"}),
    )
    other = RequestActor(
        user_id=2,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"chat.start", "chat.read"}),
    )
    await service.create_conversation(CreateConversationInput(title="A"), owner)
    await service.create_conversation(CreateConversationInput(title="B"), owner)
    await service.create_conversation(CreateConversationInput(title="C"), other)
    deleted = await service.delete_all_conversations(owner)
    assert deleted == 2
    assert len(await service.list_conversations(owner)) == 0
    assert len(await service.list_conversations(other)) == 1
