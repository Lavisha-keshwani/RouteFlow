"""Authentication routes: register, login, refresh, current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.domain.errors import AuthenticationError
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    RefreshRequest,
    TokenPair,
    UserLogin,
    UserOut,
    UserRegister,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account",
)
def register(data: UserRegister, db: Session = Depends(get_db)) -> AuthResponse:
    service = AuthService(db)
    user = service.register_customer(data)
    return AuthResponse(user=UserOut.model_validate(user), tokens=service.issue_tokens(user))


@router.post("/login", response_model=AuthResponse, summary="Log in and receive JWT tokens")
def login(data: UserLogin, db: Session = Depends(get_db)) -> AuthResponse:
    service = AuthService(db)
    user = service.authenticate(data.email, data.password)
    return AuthResponse(user=UserOut.model_validate(user), tokens=service.issue_tokens(user))


@router.post("/refresh", response_model=TokenPair, summary="Exchange a refresh token")
def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token.")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive.")
    return TokenPair(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id), user.role.value),
    )


@router.get("/me", response_model=UserOut, summary="Get the current authenticated user")
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
