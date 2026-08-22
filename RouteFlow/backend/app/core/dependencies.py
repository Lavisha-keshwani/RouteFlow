"""FastAPI dependencies: authentication, RBAC and service wiring.

Authorization is always enforced server-side here — never trust the frontend.
"""
from __future__ import annotations

from typing import Callable, Iterable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.domain.enums import UserRole
from app.domain.errors import AuthenticationError, PermissionDeniedError
from app.models.user import Customer, DeliveryAgent, User
from app.notifications.service import NotificationService
from app.utils.logging import user_id_ctx

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and validate the authenticated user from a Bearer JWT."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing or invalid authorization header.")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise AuthenticationError("Invalid or expired access token.")

    user_id = payload.get("sub")
    user = db.get(User, int(user_id)) if user_id else None
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive.")

    user_id_ctx.set(str(user.id))
    request.state.user_id = user.id
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Dependency factory enforcing that the user holds one of ``roles``."""

    allowed: Iterable[UserRole] = roles

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError(
                "You do not have permission to perform this action."
            )
        return user

    return _dependency


def get_current_customer(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Customer:
    """Return the Customer profile for the authenticated customer user."""
    if user.role != UserRole.CUSTOMER:
        raise PermissionDeniedError("Customer access required.")
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if customer is None:
        raise AuthenticationError("Customer profile not found.")
    return customer


def get_current_agent(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DeliveryAgent:
    """Return the DeliveryAgent profile for the authenticated agent user."""
    if user.role != UserRole.DELIVERY_AGENT:
        raise PermissionDeniedError("Delivery agent access required.")
    agent = db.query(DeliveryAgent).filter(DeliveryAgent.user_id == user.id).first()
    if agent is None:
        raise AuthenticationError("Agent profile not found.")
    return agent


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


# Convenience role dependencies
require_admin = require_roles(UserRole.ADMIN)
require_agent = require_roles(UserRole.DELIVERY_AGENT)
require_customer = require_roles(UserRole.CUSTOMER)
