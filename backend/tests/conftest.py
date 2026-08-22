"""Shared pytest fixtures.

Each test runs against a fresh in-memory SQLite database seeded with the same
demo data used by the CLI seeder, guaranteeing isolation. A new session is
created per request (as in production) while all sessions share the single
in-memory connection via ``StaticPool``.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  registers all tables on Base
from app.core import security as security_module
from app.core.database import Base, get_db
from app.core.rate_limit import limiter
from app.main import app
from app.seeds import seed_data
from app.seeds.seed_data import (
    ADMIN_EMAIL,
    AGENT_EMAIL,
    CUSTOMER_EMAIL,
    DEMO_PASSWORD,
    seed,
)

# Rate limiting would otherwise trip across the many requests a suite makes.
limiter.enabled = False

# Hash the shared demo password once; reuse it for every seeded user so seeding
# stays fast without weakening the real hashing used by the login endpoint.
_CACHED_HASH = security_module.hash_password(DEMO_PASSWORD)
_REAL_HASH = security_module.hash_password


def _fast_hash(password: str) -> str:
    return _CACHED_HASH if password == DEMO_PASSWORD else _REAL_HASH(password)


seed_data.hash_password = _fast_hash  # type: ignore[assignment]


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, future=True
    )
    seed_session = testing_session()
    try:
        seed(seed_session, with_orders=False)
    finally:
        seed_session.close()
    try:
        yield testing_session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_engine):
    testing_session = db_engine

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> dict:
    """Log in and return an Authorization header for the given account."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client) -> dict:
    return auth_header(client, ADMIN_EMAIL)


@pytest.fixture
def customer_headers(client) -> dict:
    return auth_header(client, CUSTOMER_EMAIL)


@pytest.fixture
def agent_headers(client) -> dict:
    return auth_header(client, AGENT_EMAIL)
