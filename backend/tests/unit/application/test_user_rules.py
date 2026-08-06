"""Unit tests for user field validation rules."""

import pytest

from app.application.services.user.user_rules import (
    normalize_username,
    validate_avatar_url,
    validate_password,
)
from app.domain.exceptions.user import UserValidationError


def test_password_policy() -> None:
    assert validate_password("Str0ng!Password")
    with pytest.raises(UserValidationError):
        validate_password("nouppercase1!")
    with pytest.raises(UserValidationError):
        validate_password("NOLOWERCASE1!")
    with pytest.raises(UserValidationError):
        validate_password("NoNumber!!Abc")
    with pytest.raises(UserValidationError):
        validate_password("NoSpecial12345")


def test_username_and_avatar() -> None:
    assert normalize_username("Ada_Lovelace") == "ada_lovelace"
    with pytest.raises(UserValidationError):
        normalize_username("ab")
    assert validate_avatar_url("https://cdn.example.com/a.png")
    assert validate_avatar_url("/storage/avatars/1.png")
    with pytest.raises(UserValidationError):
        validate_avatar_url("http://insecure.example.com/a.png")
