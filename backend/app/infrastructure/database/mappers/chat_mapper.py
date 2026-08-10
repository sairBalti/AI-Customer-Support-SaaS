"""Map chat ORM models to domain entities."""

from __future__ import annotations

from decimal import Decimal

from app.domain.entities.chat_message import ChatMessage
from app.domain.entities.chat_session import ChatSession
from app.domain.enums.chat_status import (
    ChatMessageFeedback,
    ChatMessageType,
    ChatSenderType,
    ChatSessionStatus,
)
from app.infrastructure.database.models.chat_message import ChatMessageModel
from app.infrastructure.database.models.chat_session import ChatSessionModel


def chat_session_to_entity(model: ChatSessionModel) -> ChatSession:
    return ChatSession(
        session_id=int(model.session_id),
        company_id=int(model.company_id),
        customer_id=int(model.customer_id),
        session_uuid=model.session_uuid,
        title=model.title,
        language=model.language,
        ai_provider=model.ai_provider,
        ai_model=model.ai_model,
        session_status=ChatSessionStatus(model.session_status),
        total_messages=int(model.total_messages),
        total_prompt_tokens=int(model.total_prompt_tokens),
        total_completion_tokens=int(model.total_completion_tokens),
        total_tokens=int(model.total_tokens),
        estimated_cost=Decimal(model.estimated_cost),
        customer_satisfaction=model.customer_satisfaction,
        escalation_required=bool(model.escalation_required),
        escalated_at=model.escalated_at,
        ticket_id=int(model.ticket_id) if model.ticket_id is not None else None,
        last_message_at=model.last_message_at,
        archived_at=model.archived_at,
        metadata=dict(model.metadata_ or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def chat_message_to_entity(model: ChatMessageModel) -> ChatMessage:
    feedback = ChatMessageFeedback(model.feedback) if model.feedback else None
    return ChatMessage(
        message_id=int(model.message_id),
        session_id=int(model.session_id),
        company_id=int(model.company_id),
        sender_id=int(model.sender_id) if model.sender_id is not None else None,
        parent_message_id=(
            int(model.parent_message_id) if model.parent_message_id is not None else None
        ),
        message_uuid=model.message_uuid,
        message_type=ChatMessageType(model.message_type),
        sender_type=ChatSenderType(model.sender_type),
        message_text=model.message_text,
        formatted_message=model.formatted_message,
        ai_model=model.ai_model,
        ai_provider=model.ai_provider,
        prompt_tokens=int(model.prompt_tokens),
        completion_tokens=int(model.completion_tokens),
        total_tokens=int(model.total_tokens),
        estimated_cost=Decimal(model.estimated_cost),
        response_time_ms=model.response_time_ms,
        confidence_score=(
            Decimal(model.confidence_score) if model.confidence_score is not None else None
        ),
        retrieved_chunks=list(model.retrieved_chunks or []),
        citations=[dict(c) for c in (model.citations or [])],
        metadata=dict(model.metadata_ or {}),
        feedback=feedback,
        is_escalated=bool(model.is_escalated),
        created_at=model.created_at,
    )
