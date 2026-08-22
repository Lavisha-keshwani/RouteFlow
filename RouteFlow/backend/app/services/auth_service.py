"""Authentication service: registration, login and token issuance."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.domain.enums import UserRole
from app.domain.errors import AuthenticationError, DuplicateResourceError
from app.models.user import Customer, User
from app.schemas.auth import TokenPair, UserRegister
from app.utils.logging import get_logger, log_event

logger = get_logger("services.auth")


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register_customer(self, data: UserRegister) -> User:
        existing = self.db.query(User).filter(User.email == data.email.lower()).first()
        if existing:
            raise DuplicateResourceError("An account with this email already exists.")

        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()

        self.db.add(Customer(user_id=user.id))
        self.db.commit()
        self.db.refresh(user)
        log_event(logger, "customer_registered", user_id=user.id)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.db.query(User).filter(User.email == email.lower()).first()
        if user is None or not verify_password(password, user.password_hash):
            # Uniform error avoids leaking which accounts exist.
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated.")
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(str(user.id), user.role.value),
            refresh_token=create_refresh_token(str(user.id), user.role.value),
        )
