"""Audit service: append-only trail for important admin operations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.system import AuditLog
from app.models.user import User


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        actor: Optional[User],
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
    ) -> None:
        """Add an audit row to the current transaction (caller commits)."""
        self.db.add(
            AuditLog(
                actor_id=actor.id if actor else None,
                actor_role=actor.role if actor else None,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                old_value=old_value,
                new_value=new_value,
                created_at=datetime.now(timezone.utc),
            )
        )
