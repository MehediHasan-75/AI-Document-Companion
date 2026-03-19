"""Authentication service: password hashing and JWT management."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.config import settings
from src.core.exceptions import AuthenticationError, ConflictError, ForbiddenError
from src.models.user import User

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise AuthenticationError("Invalid or expired token")
    if not payload.get("sub"):
        raise AuthenticationError("Invalid token: missing subject")
    return payload


class AuthService:
    """Handles user registration, login, and token operations."""

    def register(
        self, db: Session, email: str, password: str, full_name: Optional[str] = None
    ) -> User:
        if db.query(User).filter(User.email == email).first():
            raise ConflictError("An account with this email already exists")

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Registered new user: %s", email)
        return user

    def authenticate(self, db: Session, email: str, password: str) -> User:
        user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        return user

    def get_by_id(self, db: Session, user_id: str) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")
        if not user.is_active:
            raise ForbiddenError("Account is deactivated")
        return user


auth_service = AuthService()
