"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> dict:
    """Return a simple liveness signal."""
    return {"status": "healthy"}


@router.get("/health/ready", summary="Readiness probe")
def readiness(db: Session = Depends(get_db)) -> dict:
    """Verify database connectivity for readiness checks."""
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}
