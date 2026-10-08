"""Least-load automated ticket routing among support staff."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.enums.user_status import UserStatus
from app.domain.interfaces.repositories.ticket_repository import TicketRepository
from app.domain.interfaces.repositories.user_repository import UserRepository

# Prefer agents; managers are a fallback when no agent is available.
_ROUTABLE_ROLE_NAMES: tuple[str, ...] = ("SUPPORT_AGENT", "SUPPORT_MANAGER")


async def select_assignee(
    *,
    company_id: int,
    users: UserRepository,
    tickets: TicketRepository,
) -> int | None:
    """Pick the active support user with the fewest open/in-progress tickets.

    Returns ``None`` when no routable staff exist for the company.
    Ties break by lowest ``user_id`` (stable round-robin seed).
    """
    for role_name in _ROUTABLE_ROLE_NAMES:
        role_id = await users.get_role_id_by_name(role_name)
        if role_id is None:
            continue
        candidates, _ = await users.search(
            search=None,
            status=UserStatus.ACTIVE,
            role_id=role_id,
            company_id=company_id,
            page=1,
            page_size=200,
            sort_by="created_at",
            sort_order="asc",
            include_deleted=False,
        )
        if not candidates:
            continue
        assignee_ids = sorted(u.user_id for u in candidates)
        loads = await tickets.count_active_by_assignee(
            company_id=company_id,
            assignee_ids=assignee_ids,
        )
        return _pick_least_loaded(assignee_ids, loads)
    return None


def _pick_least_loaded(assignee_ids: Sequence[int], loads: dict[int, int]) -> int:
    return min(assignee_ids, key=lambda uid: (loads.get(uid, 0), uid))
