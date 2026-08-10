"""Chat / support agent application DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.entities.chat_message import ChatMessage
from app.domain.entities.chat_session import ChatSession


@dataclass(slots=True)
class CreateConversationInput:
    title: str | None = None
    language: str = "en"


@dataclass(slots=True)
class SendChatMessageInput:
    content: str


@dataclass(slots=True)
class ChatAnswerResult:
    conversation: ChatSession
    user_message: ChatMessage
    assistant_message: ChatMessage
    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    used_knowledge: bool = False
