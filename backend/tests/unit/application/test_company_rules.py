"""Unit tests for company slug / validation helpers."""

import pytest

from app.application.services.company.company_rules import (
    escape_like,
    normalize_website,
    slugify,
    validate_phone,
    validate_slug,
    validate_sort_by,
)
from app.domain.exceptions.company import CompanyValidationError


def test_slugify_basic() -> None:
    assert slugify("Acme Corporation") == "acme-corporation"


def test_validate_slug_rejects_spaces() -> None:
    with pytest.raises(CompanyValidationError):
        validate_slug("Acme Corp")


def test_validate_phone_e164() -> None:
    assert validate_phone("+15551234567") == "+15551234567"
    with pytest.raises(CompanyValidationError):
        validate_phone("555-1234")


def test_normalize_website_rejects_bad_url() -> None:
    with pytest.raises(CompanyValidationError):
        normalize_website("not a url")


def test_escape_like_wildcards() -> None:
    assert escape_like("100%_off") == r"100\%\_off"


def test_validate_sort_by() -> None:
    assert validate_sort_by("company_name") == "company_name"
    with pytest.raises(CompanyValidationError):
        validate_sort_by("password")
