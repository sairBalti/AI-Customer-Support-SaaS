"""Subscription plan enumeration."""

from enum import StrEnum


class SubscriptionPlan(StrEnum):
    """Company subscription plan tiers."""

    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    BUSINESS = "BUSINESS"
    ENTERPRISE = "ENTERPRISE"
