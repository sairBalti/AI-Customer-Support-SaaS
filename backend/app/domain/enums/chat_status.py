"""Chat session and message enumerations."""

from __future__ import annotations

from enum import StrEnum


class ChatSessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WAITING_CUSTOMER = "WAITING_CUSTOMER"
    WAITING_AI = "WAITING_AI"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"
    EXPIRED = "EXPIRED"


class ChatSenderType(StrEnum):
    CUSTOMER = "CUSTOMER"
    AI = "AI"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


class ChatMessageType(StrEnum):
    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"
    IMAGE = "IMAGE"
    FILE = "FILE"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class ChatMessageFeedback(StrEnum):
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    NEUTRAL = "NEUTRAL"
