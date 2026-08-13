"""AI Customer Support Agent — grounded RAG chat service."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.application.context import RequestActor
from app.application.dto.chat import ChatAnswerResult, CreateConversationInput, SendChatMessageInput
from app.application.services.chat.prompts import (
    GROUNDED_SYSTEM_PROMPT,
    NO_CONTEXT_ANSWER,
    citations_from_chunks,
    format_retrieval_context,
)
from app.core.security.rbac import ensure_permissions
from app.domain.entities.chat_message import ChatMessage
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.knowledge_chunk import RetrievedChunk
from app.domain.enums.chat_status import (
    ChatMessageType,
    ChatSenderType,
    ChatSessionStatus,
)
from app.domain.enums.document_status import DocumentStatus
from app.domain.exceptions.chat import (
    ChatAccessDeniedError,
    ChatNotFoundError,
    ChatOperationForbiddenError,
    ChatValidationError,
)
from app.domain.interfaces.repositories.chat_message_repository import ChatMessageRepository
from app.domain.interfaces.repositories.chat_session_repository import ChatSessionRepository
from app.domain.interfaces.repositories.document_repository import DocumentRepository
from app.domain.interfaces.services.audit_logger import AuditLogger
from app.domain.interfaces.services.embedding_service import EmbeddingProvider
from app.domain.interfaces.services.llm_client import LlmChatTurn, LlmClient
from app.domain.interfaces.services.vector_store import VectorStore


class ChatService:
    """Orchestrates conversations and grounded RAG answers."""

    def __init__(
        self,
        *,
        sessions: ChatSessionRepository,
        messages: ChatMessageRepository,
        documents: DocumentRepository,
        embeddings: EmbeddingProvider,
        vectors: VectorStore,
        llm: LlmClient,
        audit_logger: AuditLogger,
        top_k: int = 5,
    ) -> None:
        self._sessions = sessions
        self._messages = messages
        self._documents = documents
        self._embeddings = embeddings
        self._vectors = vectors
        self._llm = llm
        self._audit = audit_logger
        self._top_k = top_k if top_k > 0 else 5
        self._pending_audits: list[dict[str, Any]] = []

    async def flush_audits(self) -> None:
        """Persist queued audit events on the current session before commit."""
        if not self._pending_audits:
            return
        events = list(self._pending_audits)
        for event in events:
            await self._audit.log(**event)
        self._pending_audits.clear()

    def discard_audits(self) -> None:
        self._pending_audits.clear()

    async def create_conversation(
        self,
        data: CreateConversationInput,
        actor: RequestActor,
    ) -> ChatSession:
        ensure_permissions(actor, "chat.start")
        company_id = self._require_company_id(actor)
        if actor.user_id is None:
            raise ChatValidationError("Authenticated user is required.")
        now = datetime.now(UTC)
        session = await self._sessions.create(
            {
                "company_id": company_id,
                "customer_id": int(actor.user_id),
                "session_uuid": str(uuid.uuid4()),
                "title": (data.title or "").strip() or None,
                "language": (data.language or "en").strip() or "en",
                "ai_provider": self._llm.provider_name,
                "ai_model": self._llm.model_name,
                "session_status": ChatSessionStatus.ACTIVE,
                "total_messages": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": Decimal("0"),
                "escalation_required": False,
                "created_at": now,
                "updated_at": now,
                "metadata": {},
            }
        )
        self._queue_audit(
            action="chat.conversation.create",
            entity_id=session.session_id,
            company_id=company_id,
            user_id=actor.user_id,
        )
        return session

    async def list_conversations(
        self,
        actor: RequestActor,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSession]:
        ensure_permissions(actor, "chat.read")
        company_id = self._require_company_id(actor)
        customer_id = None
        if self._is_customer(actor):
            customer_id = actor.user_id
        return await self._sessions.list_by_company(
            company_id,
            customer_id=customer_id,
            limit=min(max(limit, 1), 100),
            offset=max(offset, 0),
        )

    async def get_conversation(
        self,
        conversation_id: int,
        actor: RequestActor,
    ) -> tuple[ChatSession, list[ChatMessage]]:
        ensure_permissions(actor, "chat.read")
        session = await self._load_conversation_for_actor(conversation_id, actor)
        messages = await self._messages.list_by_session(
            session.session_id,
            company_id=session.company_id,
        )
        return session, messages

    async def delete_conversation(self, conversation_id: int, actor: RequestActor) -> None:
        ensure_permissions(actor, "chat.start")
        session = await self._load_conversation_for_actor(
            conversation_id,
            actor,
            require_write=True,
        )
        await self._messages.delete_by_session(
            session.session_id,
            company_id=session.company_id,
        )
        deleted = await self._sessions.delete_by_id(
            session.session_id,
            company_id=session.company_id,
        )
        if not deleted:
            raise ChatNotFoundError()
        self._queue_audit(
            action="chat.conversation.delete",
            entity_id=session.session_id,
            company_id=session.company_id,
            user_id=actor.user_id,
        )

    async def delete_all_conversations(self, actor: RequestActor) -> int:
        ensure_permissions(actor, "chat.start")
        company_id = self._require_company_id(actor)
        customer_id = actor.user_id if self._is_customer(actor) else None
        sessions = await self._sessions.list_by_company(
            company_id,
            customer_id=customer_id,
            limit=10_000,
            offset=0,
        )
        for session in sessions:
            await self._messages.delete_by_session(
                session.session_id,
                company_id=company_id,
            )
        count = await self._sessions.delete_by_company(company_id, customer_id=customer_id)
        self._queue_audit(
            action="chat.conversation.delete_all",
            entity_id=0,
            company_id=company_id,
            user_id=actor.user_id,
            metadata={"deleted_count": count},
        )
        return count

    async def send_message(
        self,
        conversation_id: int,
        data: SendChatMessageInput,
        actor: RequestActor,
    ) -> ChatAnswerResult:
        ensure_permissions(actor, "chat.start")
        content = (data.content or "").strip()
        if not content:
            raise ChatValidationError("message content is required.")
        session = await self._load_conversation_for_actor(
            conversation_id,
            actor,
            require_write=True,
        )
        if not session.accepts_messages:
            raise ChatOperationForbiddenError(
                "This conversation is closed and cannot accept new messages.",
            )

        now = datetime.now(UTC)
        user_msg = await self._messages.create(
            {
                "session_id": session.session_id,
                "company_id": session.company_id,
                "sender_id": actor.user_id,
                "message_uuid": str(uuid.uuid4()),
                "message_type": ChatMessageType.TEXT,
                "sender_type": ChatSenderType.CUSTOMER,
                "message_text": content,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": Decimal("0"),
                "retrieved_chunks": [],
                "citations": [],
                "metadata": {},
                "is_escalated": False,
                "created_at": now,
            }
        )

        chunks = await self._retrieve_company_chunks(
            company_id=session.company_id,
            query=content,
        )
        sources = await self._build_sources(chunks)
        used_knowledge = bool(chunks)
        started = time.perf_counter()

        if not used_knowledge:
            answer = NO_CONTEXT_ANSWER
            llm_provider = self._llm.provider_name
            llm_model = self._llm.model_name
            prompt_tokens = 0
            completion_tokens = max(1, len(answer) // 4)
        else:
            history_messages = await self._messages.list_by_session(
                session.session_id,
                company_id=session.company_id,
                limit=20,
            )
            history = [
                LlmChatTurn(
                    role="user" if m.sender_type == ChatSenderType.CUSTOMER else "assistant",
                    content=m.message_text,
                )
                for m in history_messages
                if m.message_id != user_msg.message_id
                and m.sender_type in {ChatSenderType.CUSTOMER, ChatSenderType.AI}
            ]
            context = format_retrieval_context(chunks)
            generation = await self._llm.generate_response(
                system_prompt=GROUNDED_SYSTEM_PROMPT,
                user_message=content,
                context=context,
                history=history,
            )
            answer = (generation.content or "").strip() or NO_CONTEXT_ANSWER
            llm_provider = generation.provider
            llm_model = generation.model
            prompt_tokens = int(generation.prompt_tokens)
            completion_tokens = int(generation.completion_tokens)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        assistant_msg = await self._messages.create(
            {
                "session_id": session.session_id,
                "company_id": session.company_id,
                "sender_id": None,
                "parent_message_id": user_msg.message_id,
                "message_uuid": str(uuid.uuid4()),
                "message_type": ChatMessageType.TEXT,
                "sender_type": ChatSenderType.AI,
                "message_text": answer,
                "ai_model": llm_model,
                "ai_provider": llm_provider,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "estimated_cost": Decimal("0"),
                "response_time_ms": elapsed_ms,
                "retrieved_chunks": [
                    {
                        "chunk_uuid": c.chunk_uuid,
                        "document_id": c.document_id,
                        "score": c.score,
                    }
                    for c in chunks
                ],
                "citations": sources,
                "metadata": {"used_knowledge": used_knowledge},
                "is_escalated": False,
                "created_at": datetime.now(UTC),
            }
        )

        title = session.title
        if not title:
            title = content[:80]

        updated = await self._sessions.update(
            session.session_id,
            {
                "title": title,
                "total_messages": session.total_messages + 2,
                "total_prompt_tokens": session.total_prompt_tokens + prompt_tokens,
                "total_completion_tokens": session.total_completion_tokens + completion_tokens,
                "total_tokens": session.total_tokens + prompt_tokens + completion_tokens,
                "last_message_at": datetime.now(UTC),
                "session_status": ChatSessionStatus.ACTIVE,
                "ai_provider": llm_provider,
                "ai_model": llm_model,
                "updated_at": datetime.now(UTC),
            },
            company_id=session.company_id,
        )
        assert updated is not None

        self._queue_audit(
            action="chat.message.send",
            entity_id=session.session_id,
            company_id=session.company_id,
            user_id=actor.user_id,
            metadata={
                "used_knowledge": used_knowledge,
                "sources": len(sources),
                "provider": llm_provider,
            },
        )
        return ChatAnswerResult(
            conversation=updated,
            user_message=user_msg,
            assistant_message=assistant_msg,
            answer=answer,
            sources=sources,
            used_knowledge=used_knowledge,
        )

    async def _retrieve_company_chunks(
        self,
        *,
        company_id: int,
        query: str,
    ) -> list[RetrievedChunk]:
        """Internal RAG retrieval — always filtered by company_id (no knowledge.search)."""
        query_vectors = await self._embeddings.embed_texts([query])
        hits = await self._vectors.similarity_search(
            company_id=company_id,
            query_embedding=query_vectors[0],
            top_k=self._top_k,
        )
        results: list[RetrievedChunk] = []
        for hit in hits:
            meta = hit.metadata or {}
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
            results.append(
                RetrievedChunk(
                    document_id=doc_id,
                    chunk_id=(int(meta["chunk_id"]) if meta.get("chunk_id") is not None else None),
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
        return results

    async def _build_sources(self, chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
        names: dict[int, str] = {}
        for chunk in chunks:
            if chunk.document_id in names:
                continue
            document = await self._documents.get_by_id(chunk.document_id)
            if document is not None:
                names[chunk.document_id] = document.document_name
        return citations_from_chunks(chunks, document_names=names)

    async def _load_conversation_for_actor(
        self,
        conversation_id: int,
        actor: RequestActor,
        *,
        require_write: bool = False,
    ) -> ChatSession:
        company_id = self._require_company_id(actor)
        session = await self._sessions.get_by_id(conversation_id, company_id=company_id)
        if session is None:
            # Hide cross-tenant existence.
            other = await self._sessions.get_by_id(conversation_id)
            if other is not None and other.company_id != company_id:
                raise ChatAccessDeniedError(
                    "Cannot access a conversation belonging to another company.",
                )
            raise ChatNotFoundError()
        if self._is_customer(actor) and session.customer_id != actor.user_id:
            raise ChatAccessDeniedError("Customers may only access their own conversations.")
        if require_write and self._is_customer(actor) and session.customer_id != actor.user_id:
            raise ChatAccessDeniedError("Customers may only message their own conversations.")
        return session

    def _require_company_id(self, actor: RequestActor) -> int:
        if actor.company_id is None:
            raise ChatValidationError("company context is required.")
        return int(actor.company_id)

    @staticmethod
    def _is_customer(actor: RequestActor) -> bool:
        return (actor.role_name or "").upper() == "CUSTOMER"

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
                "entity": "chat_session",
                "entity_id": entity_id,
                "company_id": company_id,
                "user_id": user_id,
                "metadata": metadata or {},
            }
        )
