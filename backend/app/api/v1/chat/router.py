"""Chat / AI Support Agent API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.api.deps import ChatServiceDep, DbSession
from app.api.security import RequireChatRead, RequireChatStart
from app.api.v1.chat.schemas import (
    ChatMessageResponse,
    ChatSourceResponse,
    ConversationResponse,
    CreateConversationRequest,
    SendMessageRequest,
    SendMessageResponse,
)
from app.application.dto.chat import CreateConversationInput, SendChatMessageInput
from app.application.use_cases.chat import (
    CreateConversationUseCase,
    GetConversationUseCase,
    ListConversationsUseCase,
    SendChatMessageUseCase,
)
from app.core.responses.envelopes import success_envelope
from app.domain.entities.chat_message import ChatMessage
from app.domain.entities.chat_session import ChatSession

router = APIRouter(prefix="/chat", tags=["Chat"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid JWT"},
    403: {"description": "Insufficient permission or tenant isolation"},
    404: {"description": "Conversation not found"},
}


def _conversation_payload(session: ChatSession) -> dict[str, Any]:
    return ConversationResponse(
        conversation_id=session.session_id,
        conversation_uuid=session.session_uuid,
        company_id=session.company_id,
        customer_id=session.customer_id,
        title=session.title,
        language=session.language,
        status=session.session_status.value,
        total_messages=session.total_messages,
        ai_provider=session.ai_provider,
        ai_model=session.ai_model,
        last_message_at=session.last_message_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    ).model_dump(mode="json")


def _message_payload(message: ChatMessage) -> dict[str, Any]:
    return ChatMessageResponse(
        message_id=message.message_id,
        message_uuid=message.message_uuid,
        conversation_id=message.session_id,
        company_id=message.company_id,
        sender_type=message.sender_type.value,
        message_type=message.message_type.value,
        content=message.message_text,
        citations=list(message.citations or []),
        ai_provider=message.ai_provider,
        ai_model=message.ai_model,
        created_at=message.created_at,
    ).model_dump(mode="json")


@router.post(
    "/conversations",
    summary="Start a support conversation",
    status_code=201,
    responses=_AUTH_RESPONSES,
)
async def create_conversation(
    body: CreateConversationRequest,
    session: DbSession,
    service: ChatServiceDep,
    actor: RequireChatStart,
) -> dict[str, Any]:
    created = await CreateConversationUseCase(session, service).execute(
        CreateConversationInput(title=body.title, language=body.language),
        actor,
    )
    return success_envelope(_conversation_payload(created))


@router.get(
    "/conversations",
    summary="List company conversations",
    responses=_AUTH_RESPONSES,
)
async def list_conversations(
    session: DbSession,
    service: ChatServiceDep,
    actor: RequireChatRead,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = await ListConversationsUseCase(session, service).execute(
        actor,
        limit=limit,
        offset=offset,
    )
    return success_envelope({"items": [_conversation_payload(i) for i in items]})


@router.get(
    "/conversations/{conversation_id}",
    summary="Get conversation with messages",
    responses=_AUTH_RESPONSES,
)
async def get_conversation(
    conversation_id: int,
    session: DbSession,
    service: ChatServiceDep,
    actor: RequireChatRead,
) -> dict[str, Any]:
    conversation, messages = await GetConversationUseCase(session, service).execute(
        conversation_id,
        actor,
    )
    return success_envelope(
        {
            "conversation": _conversation_payload(conversation),
            "messages": [_message_payload(m) for m in messages],
        }
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    summary="Send a message and receive a grounded AI answer",
    responses=_AUTH_RESPONSES,
)
async def send_message(
    conversation_id: int,
    body: SendMessageRequest,
    session: DbSession,
    service: ChatServiceDep,
    actor: RequireChatStart,
) -> dict[str, Any]:
    result = await SendChatMessageUseCase(session, service).execute(
        conversation_id,
        SendChatMessageInput(content=body.content),
        actor,
    )
    payload = SendMessageResponse(
        answer=result.answer,
        sources=[ChatSourceResponse.model_validate(s) for s in result.sources],
        used_knowledge=result.used_knowledge,
        conversation=ConversationResponse.model_validate(
            _conversation_payload(result.conversation)
        ),
        user_message=ChatMessageResponse.model_validate(_message_payload(result.user_message)),
        assistant_message=ChatMessageResponse.model_validate(
            _message_payload(result.assistant_message)
        ),
    )
    return success_envelope(payload.model_dump(mode="json"))
