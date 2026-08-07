"""SQLAlchemy database package.

Public surface for async engine/session wiring and declarative Base.
ORM entity models live under ``models/`` and are added separately.
"""

from app.infrastructure.database.base import NAMING_CONVENTION, Base, metadata
from app.infrastructure.database.session import (
    check_database_connection,
    dispose_engine,
    get_db,
    get_engine,
    get_session_factory,
)

__all__ = [
    "Base",
    "NAMING_CONVENTION",
    "metadata",
    "check_database_connection",
    "dispose_engine",
    "get_db",
    "get_engine",
    "get_session_factory",
]
