"""Ticket node — create a support ticket and auto-route it to an agent."""

from __future__ import annotations

from typing import Any

from app.agents.state import AgentState
from app.agents.tools.create_ticket import CreateTicketToolContext, create_ticket
from app.application.context import RequestActor
from app.application.services.ticket.ticket_service import TicketService


def _actor_from_state(state: AgentState) -> RequestActor:
    return RequestActor(
        user_id=state["user_id"],
        company_id=state["company_id"],
        role_name=state.get("role_name"),
        permissions=frozenset(state.get("permissions") or ()),
    )


async def ticket_node(
    state: AgentState,
    *,
    tickets: TicketService,
) -> dict[str, Any]:
    """LangGraph-compatible ticket node.

    Runs when ``should_escalate`` is true (or already set by the decision node).
    Creates a ticket via the create_ticket tool and applies automated routing.
    """
    if not state.get("should_escalate", True):
        return {"ticket_id": None, "assigned_to": None}

    subject = (state.get("subject") or "Support escalation").strip()
    description = (state.get("description") or "").strip()
    if not description:
        description = "Escalated by support agent."

    ctx = CreateTicketToolContext(tickets=tickets, actor=_actor_from_state(state))
    try:
        result = await create_ticket(
            ctx,
            subject=subject,
            description=description,
            conversation_id=state.get("conversation_id"),
            source_message_id=state.get("source_message_id"),
            customer_id=state.get("customer_id"),
            priority=state.get("priority"),
            category=state.get("category"),
            auto_route=True,
        )
    except Exception as exc:  # noqa: BLE001 — surface to graph without crashing pipeline
        return {
            "ticket_id": None,
            "ticket_number": None,
            "assigned_to": None,
            "error": str(exc),
        }

    return {
        "ticket_id": result["ticket_id"],
        "ticket_number": result["ticket_number"],
        "assigned_to": result["assigned_to"],
        "error": None,
        "metadata": {
            **(state.get("metadata") or {}),
            "ticket_routed": result["routed"],
            "ticket_status": result["status"],
        },
    }
