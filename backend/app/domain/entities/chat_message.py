"""Chat message domain entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.enums.chat_status import ChatMessageFeedback, ChatMessageType, ChatSenderType


@dataclass(slots=True)
class ChatMessage:
    message_id: int
    session_id: int
    company_id: int
    message_uuid: str
    message_type: ChatMessageType
    sender_type: ChatSenderType
    message_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: Decimal
    is_escalated: bool
    created_at: datetime
    sender_id: int | None = None
    parent_message_id: int | None = None
    formatted_message: str | None = None
    ai_model: str | None = None
    ai_provider: str | None = None
    response_time_ms: int | None = None
    confidence_score: Decimal | None = None
    retrieved_chunks: list[Any] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    feedback: ChatMessageFeedback | None = None
