"""Database engine, session factory and declarative base.

Uses SQLAlchemy 2.x style with a scoped session dependency for FastAPI.
"""
from __future__ import annotations

from typing import Any, Dict, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def _engine_kwargs() -> Dict[str, Any]:
    """Build engine kwargs appropriate for the configured database.

    PostgreSQL (production) uses a sized connection pool; SQLite (handy for local
    demos and tests) needs different pool settings and cannot accept ``pool_size``.
    """
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        kwargs: Dict[str, Any] = {
            "future": True,
            "connect_args": {"check_same_thread": False},
        }
        if ":memory:" in url or url in ("sqlite://",):
            kwargs["poolclass"] = StaticPool
        return kwargs
    return {
        "future": True,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
    }


engine = create_engine(settings.DATABASE_URL, **_engine_kwargs())

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator:
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
