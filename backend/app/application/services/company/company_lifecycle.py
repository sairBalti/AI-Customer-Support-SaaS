"""Company lifecycle / transition policy."""

from __future__ import annotations

from app.domain.enums.company_status import CompanyStatus
from app.domain.exceptions.company import CompanyValidationError

# Documented flow: Trial → Active → Suspended → Inactive → Archived
# Super Admin may also reactivate from Suspended/Inactive.
ALLOWED_STATUS_TRANSITIONS: dict[CompanyStatus, frozenset[CompanyStatus]] = {
    CompanyStatus.TRIAL: frozenset(
        {
            CompanyStatus.ACTIVE,
            CompanyStatus.SUSPENDED,
            CompanyStatus.INACTIVE,
            CompanyStatus.ARCHIVED,
        }
    ),
    CompanyStatus.ACTIVE: frozenset(
        {
            CompanyStatus.SUSPENDED,
            CompanyStatus.INACTIVE,
            CompanyStatus.ARCHIVED,
            CompanyStatus.TRIAL,
        }
    ),
    CompanyStatus.SUSPENDED: frozenset(
        {
            CompanyStatus.ACTIVE,
            CompanyStatus.INACTIVE,
            CompanyStatus.ARCHIVED,
        }
    ),
    CompanyStatus.INACTIVE: frozenset(
        {
            CompanyStatus.ACTIVE,
            CompanyStatus.ARCHIVED,
            CompanyStatus.SUSPENDED,
        }
    ),
    CompanyStatus.ARCHIVED: frozenset(),  # terminal
}


def assert_status_transition(current: CompanyStatus, target: CompanyStatus) -> None:
    """Raise when a status change violates platform lifecycle rules."""
    if current == target:
        return
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise CompanyValidationError(
            f"Invalid status transition: {current.value} → {target.value}.",
        )
