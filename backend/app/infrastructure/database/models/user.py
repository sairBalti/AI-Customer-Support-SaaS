"""Backward-compatible re-export — canonical User ORM lives in ``models.auth``."""

from app.infrastructure.database.models.auth import UserModel

__all__ = ["UserModel"]
