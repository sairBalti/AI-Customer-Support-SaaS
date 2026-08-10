"""Ticket status enumeration."""

from __future__ import annotations

from enum import StrEnum


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketCategory(StrEnum):
    GENERAL = "GENERAL"
    TECHNICAL = "TECHNICAL"
    BILLING = "BILLING"
    ACCOUNT = "ACCOUNT"
    OTHER = "OTHER"


class TicketSource(StrEnum):
    AI_CHAT = "AI_CHAT"
    WEB_PORTAL = "WEB_PORTAL"
    API = "API"
    MANUAL = "MANUAL"
