"""Chat session (conversation) domain entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.enums.chat_status import ChatSessionStatus


@dataclass(slots=True)
class ChatSession:
    session_id: int
    company_id: int
    customer_id: int
    session_uuid: str
    language: str
    ai_provider: str
    ai_model: str
    session_status: ChatSessionStatus
    total_messages: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_cost: Decimal
    escalation_required: bool
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    customer_satisfaction: int | None = None
    escalated_at: datetime | None = None
    ticket_id: int | None = None
    last_message_at: datetime | None = None
    archived_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_archived(self) -> bool:
        return self.session_status == ChatSessionStatus.ARCHIVED or self.archived_at is not None

    @property
    def accepts_messages(self) -> bool:
        return self.session_status in {
            ChatSessionStatus.ACTIVE,
            ChatSessionStatus.WAITING_CUSTOMER,
            ChatSessionStatus.WAITING_AI,
        }
