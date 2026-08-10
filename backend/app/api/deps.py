"""FastAPI dependency injection providers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.services.audit.audit_log_service import AuditLogService
from app.application.services.auth.auth_service import AuthService
from app.application.services.chat.chat_service import ChatService
from app.application.services.company.company_service import CompanyService
from app.application.services.document.document_service import DocumentService
from app.application.services.knowledge.knowledge_service import KnowledgeService
from app.application.services.role.role_service import RoleService
from app.application.services.ticket.ticket_service import TicketService
from app.application.services.user.user_service import UserService
from app.core.config import Settings, get_settings
from app.core.security.http import bearer_scheme
from app.domain.enums.company_status import CompanyStatus
from app.domain.exceptions.auth import InsufficientPermissionError, TokenInvalidError
from app.domain.exceptions.company import CompanyInactiveError
from app.domain.interfaces.services.audit_logger import AuditLogger
from app.domain.interfaces.services.embedding_service import EmbeddingProvider
from app.domain.interfaces.services.llm_client import LlmClient
from app.domain.interfaces.services.object_storage import ObjectStorage
from app.domain.interfaces.services.text_chunker import TextChunker
from app.domain.interfaces.services.text_extractor import DocumentProcessor
from app.domain.interfaces.services.vector_store import VectorStore
from app.infrastructure.audit.database_audit_logger import CompositeAuditLogger
from app.infrastructure.database.repositories.audit_log_repository import (
    SQLAlchemyAuditLogRepository,
)
from app.infrastructure.database.repositories.auth_user_repository import (
    SQLAlchemyAuthUserRepository,
)
from app.infrastructure.database.repositories.chat_message_repository import (
    SQLAlchemyChatMessageRepository,
)
from app.infrastructure.database.repositories.chat_session_repository import (
    SQLAlchemyChatSessionRepository,
)
from app.infrastructure.database.repositories.company_repository import (
    SQLAlchemyCompanyRepository,
)
from app.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from app.infrastructure.database.repositories.knowledge_chunk_repository import (
    SQLAlchemyKnowledgeChunkRepository,
)
from app.infrastructure.database.repositories.refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository,
)
from app.infrastructure.database.repositories.role_repository import (
    SQLAlchemyRoleRepository,
)
from app.infrastructure.database.repositories.ticket_repository import (
    SQLAlchemyTicketRepository,
)
from app.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.knowledge.factory import (
    build_document_processor,
    build_embedding_provider,
    build_text_chunker,
    build_vector_store,
)
from app.infrastructure.llm.factory import build_llm_client
from app.infrastructure.storage.factory import build_object_storage

_ACTIVE_COMPANY_STATUSES = frozenset({CompanyStatus.ACTIVE, CompanyStatus.TRIAL})


def get_app_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_audit_logger(session: DbSession) -> AuditLogger:
    """Structured logs + persist to audit_logs on the request session."""
    return CompositeAuditLogger(session)


def get_audit_log_service(session: DbSession) -> AuditLogService:
    return AuditLogService(audit_logs=SQLAlchemyAuditLogRepository(session))


AuditLogServiceDep = Annotated[AuditLogService, Depends(get_audit_log_service)]


def get_company_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> CompanyService:
    return CompanyService(
        repository=SQLAlchemyCompanyRepository(session),
        audit_logger=audit_logger,
    )


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


def get_user_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> UserService:
    return UserService(
        users=SQLAlchemyUserRepository(session),
        companies=SQLAlchemyCompanyRepository(session),
        refresh_tokens=SQLAlchemyRefreshTokenRepository(session),
        audit_logger=audit_logger,
    )


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_role_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> RoleService:
    return RoleService(
        roles=SQLAlchemyRoleRepository(session),
        companies=SQLAlchemyCompanyRepository(session),
        audit_logger=audit_logger,
    )


RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]


def get_object_storage_dep(
    settings: SettingsDep,
) -> ObjectStorage:
    return build_object_storage(settings)


def get_document_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage_dep)],
) -> DocumentService:
    return DocumentService(
        documents=SQLAlchemyDocumentRepository(session),
        companies=SQLAlchemyCompanyRepository(session),
        storage=storage,
        audit_logger=audit_logger,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


def get_document_processor_dep(settings: SettingsDep) -> DocumentProcessor:
    return build_document_processor(settings)


def get_text_chunker_dep(settings: SettingsDep) -> TextChunker:
    return build_text_chunker(settings)


def get_embedding_provider_dep(settings: SettingsDep) -> EmbeddingProvider:
    return build_embedding_provider(settings)


def get_vector_store_dep(settings: SettingsDep) -> VectorStore:
    return build_vector_store(settings)


def get_knowledge_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage_dep)],
    processor: Annotated[DocumentProcessor, Depends(get_document_processor_dep)],
    chunker: Annotated[TextChunker, Depends(get_text_chunker_dep)],
    embeddings: Annotated[EmbeddingProvider, Depends(get_embedding_provider_dep)],
    vectors: Annotated[VectorStore, Depends(get_vector_store_dep)],
) -> KnowledgeService:
    return KnowledgeService(
        documents=SQLAlchemyDocumentRepository(session),
        chunks=SQLAlchemyKnowledgeChunkRepository(session),
        storage=storage,
        processor=processor,
        chunker=chunker,
        embeddings=embeddings,
        vectors=vectors,
        audit_logger=audit_logger,
    )


KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]


def get_llm_client_dep(settings: SettingsDep) -> LlmClient:
    return build_llm_client(settings)


def get_chat_service(
    session: DbSession,
    settings: SettingsDep,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    embeddings: Annotated[EmbeddingProvider, Depends(get_embedding_provider_dep)],
    vectors: Annotated[VectorStore, Depends(get_vector_store_dep)],
    llm: Annotated[LlmClient, Depends(get_llm_client_dep)],
) -> ChatService:
    return ChatService(
        sessions=SQLAlchemyChatSessionRepository(session),
        messages=SQLAlchemyChatMessageRepository(session),
        documents=SQLAlchemyDocumentRepository(session),
        embeddings=embeddings,
        vectors=vectors,
        llm=llm,
        audit_logger=audit_logger,
        top_k=settings.chat_top_k,
    )


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


def get_ticket_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> TicketService:
    return TicketService(
        tickets=SQLAlchemyTicketRepository(session),
        users=SQLAlchemyUserRepository(session),
        sessions=SQLAlchemyChatSessionRepository(session),
        messages=SQLAlchemyChatMessageRepository(session),
        audit_logger=audit_logger,
    )


TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]


def get_auth_service(
    session: DbSession,
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> AuthService:
    return AuthService(
        users=SQLAlchemyAuthUserRepository(session),
        refresh_tokens=SQLAlchemyRefreshTokenRepository(session),
        companies=SQLAlchemyCompanyRepository(session),
        audit_logger=audit_logger,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def _assert_company_active_for_actor(
    session: AsyncSession,
    actor: RequestActor,
) -> None:
    """Block protected APIs when the caller's tenant is not ACTIVE/TRIAL."""
    if actor.is_super_admin or actor.company_id is None:
        return
    company = await SQLAlchemyCompanyRepository(session).get_by_id(actor.company_id)
    if company is None or company.status not in _ACTIVE_COMPANY_STATUSES:
        raise CompanyInactiveError()


async def get_optional_actor(
    request: Request,
    settings: SettingsDep,
    service: AuthServiceDep,
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None,
    x_company_id: Annotated[int | None, Header(alias="X-Company-Id")] = None,
    x_super_admin: Annotated[str | None, Header(alias="X-Super-Admin")] = None,
) -> RequestActor:
    """Resolve caller from JWT when present; optional header bypass in tests."""
    auth_error = getattr(request.state, "auth_error", None)
    claims = getattr(request.state, "token_claims", None)

    if claims is not None:
        user_id = int(claims["sub"])
        user = await service.get_authenticated_user(user_id)
        actor = service.to_actor(user)
        request.state.actor = actor
        return actor

    if auth_error is not None:
        # Bearer present but invalid — preserve error for required-auth deps.
        request.state.actor = RequestActor()
        return RequestActor()

    if settings.auth_header_bypass:
        is_super_admin = False
        if x_super_admin is not None:
            is_super_admin = x_super_admin.strip().lower() in {"1", "true", "yes"}
        actor = RequestActor(
            user_id=x_user_id,
            company_id=x_company_id,
            is_super_admin=is_super_admin,
            role_name="SUPER_ADMIN" if is_super_admin else None,
            permissions=frozenset() if not is_super_admin else frozenset(),
        )
        request.state.actor = actor
        return actor

    actor = RequestActor()
    request.state.actor = actor
    return actor


OptionalActorDep = Annotated[RequestActor, Depends(get_optional_actor)]


async def get_current_actor(
    request: Request,
    session: DbSession,
    settings: SettingsDep,
    actor: OptionalActorDep,
    _credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ] = None,
) -> RequestActor:
    """Require a valid authenticated user (JWT). Alias: CurrentUser."""
    auth_error = getattr(request.state, "auth_error", None)
    if auth_error is not None:
        raise auth_error

    authenticated = actor.user_id is not None or (
        settings.auth_header_bypass and actor.is_super_admin
    )
    if not authenticated:
        raise TokenInvalidError("Authentication required.")

    await _assert_company_active_for_actor(session, actor)
    return actor


CurrentActorDep = Annotated[RequestActor, Depends(get_current_actor)]
# PRD / acceptance wording.
CurrentUserDep = CurrentActorDep


# Optional actor for public endpoints (registration, login helpers).
async def get_request_actor(actor: OptionalActorDep) -> RequestActor:
    return actor


RequestActorDep = Annotated[RequestActor, Depends(get_request_actor)]


def require_permissions(*permissions: str) -> Callable[..., Awaitable[RequestActor]]:
    """Permission dependency factory (RBAC). Requires authenticated CurrentUser."""

    async def _dependency(actor: CurrentActorDep) -> RequestActor:
        if not actor.has_all_permissions(*permissions):
            raise InsufficientPermissionError(
                f"Missing permission(s): {', '.join(permissions)}",
            )
        return actor

    return _dependency


require_permissions_dep = require_permissions
