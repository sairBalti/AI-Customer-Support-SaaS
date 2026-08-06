"""Argon2 password hashing."""

from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored Argon2 hash."""
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except Exception:  # noqa: BLE001 — treat malformed hashes as invalid
        return False
