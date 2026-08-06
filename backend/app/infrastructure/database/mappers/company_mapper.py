"""Map ORM models to domain entities."""

from __future__ import annotations

from app.domain.entities.company import Company
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.infrastructure.database.models.company import CompanyModel


def company_to_entity(model: CompanyModel) -> Company:
    """Convert a ``CompanyModel`` row into a domain ``Company``."""
    plan = model.subscription_plan
    status = model.status
    if not isinstance(plan, SubscriptionPlan):
        plan = SubscriptionPlan(str(plan))
    if not isinstance(status, CompanyStatus):
        status = CompanyStatus(str(status))

    return Company(
        company_id=int(model.company_id),
        company_name=model.company_name,
        company_slug=model.company_slug,
        legal_name=model.legal_name,
        email=model.email,
        phone=model.phone,
        website=model.website,
        logo_url=model.logo_url,
        industry=model.industry,
        country=model.country,
        timezone=model.timezone,
        subscription_plan=plan,
        max_users=int(model.max_users),
        max_documents=int(model.max_documents),
        max_storage_mb=int(model.max_storage_mb),
        monthly_ai_tokens=int(model.monthly_ai_tokens),
        token_usage=int(model.token_usage),
        status=status,
        trial_ends_at=model.trial_ends_at,
        subscription_expires_at=model.subscription_expires_at,
        last_activity_at=model.last_activity_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )
