"""User account status enumeration."""

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    LOCKED = "LOCKED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
