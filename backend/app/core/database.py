"""Compatibility exports for database sessions.

New code should import from app.db.session. This module remains so existing
services and endpoints keep working during the backend structure migration.
"""

from app.db.session import async_session_maker, close_db, engine, get_db_context, get_db_session

AsyncSessionLocal = async_session_maker
get_db = get_db_session

__all__ = [
    "AsyncSessionLocal",
    "async_session_maker",
    "close_db",
    "engine",
    "get_db",
    "get_db_context",
    "get_db_session",
]
