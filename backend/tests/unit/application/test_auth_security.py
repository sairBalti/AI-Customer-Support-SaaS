"""Unit tests for password hashing and JWT helpers."""

from app.core.security.jwt import create_access_token, decode_access_token
from app.core.security.password import hash_password, verify_password


def test_argon2_hash_and_verify() -> None:
    hashed = hash_password("Str0ng!Password")
    assert hashed != "Str0ng!Password"
    assert verify_password("Str0ng!Password", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip() -> None:
    token = create_access_token(user_id=10, company_id=20, role_name="COMPANY_ADMIN")
    payload = decode_access_token(token)
    assert payload["sub"] == "10"
    assert payload["company_id"] == 20
    assert payload["role"] == "COMPANY_ADMIN"
    assert payload["type"] == "access"
