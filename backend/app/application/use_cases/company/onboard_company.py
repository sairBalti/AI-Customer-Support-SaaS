"""Company onboarding use case (alias of create)."""

from app.application.use_cases.company.create_company import CreateCompanyUseCase

OnboardCompanyUseCase = CreateCompanyUseCase

__all__ = ["OnboardCompanyUseCase", "CreateCompanyUseCase"]
