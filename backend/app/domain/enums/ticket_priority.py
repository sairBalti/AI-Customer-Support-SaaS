"""Ticket priority enumeration."""

from __future__ import annotations

from enum import StrEnum


class TicketPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"
