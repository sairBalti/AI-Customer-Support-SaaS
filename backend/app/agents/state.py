"""Agent state shared across LangGraph support-agent nodes."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class AgentState(TypedDict):
    """Minimal state for the support pipeline (ticket node / tools)."""

    company_id: int
    user_id: int
    role_name: str
    permissions: list[str]
    conversation_id: NotRequired[int | None]
    source_message_id: NotRequired[int | None]
    customer_id: NotRequired[int | None]
    subject: NotRequired[str]
    description: NotRequired[str]
    priority: NotRequired[str]
    category: NotRequired[str]
    should_escalate: NotRequired[bool]
    ticket_id: NotRequired[int | None]
    ticket_number: NotRequired[str | None]
    assigned_to: NotRequired[int | None]
    error: NotRequired[str | None]
    metadata: NotRequired[dict[str, Any]]
