"""Authentication dependency for protected routes."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.dependencies.db import get_db
from src.models.user import User
from src.services.auth_service import auth_service, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT and return the authenticated user."""
    payload = decode_token(token)
    user_id: str = payload.get("sub")
    return auth_service.get_by_id(db, user_id)
