"""Company status enumeration."""

from enum import StrEnum


class CompanyStatus(StrEnum):
    """Lifecycle status for a company tenant."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    TRIAL = "TRIAL"
    ARCHIVED = "ARCHIVED"
