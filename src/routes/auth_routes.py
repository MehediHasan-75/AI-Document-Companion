"""Authentication routes: register, login, and current user."""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.dependencies.db import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from src.services.auth_service import auth_service, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new user",
    responses={409: {"description": "An account with this email already exists"}},
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register(db, payload.email, payload.password, payload.full_name)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT token",
    description="Use your **email** as the 'username' field (OAuth2 spec requires this field name).",
    responses={401: {"description": "Invalid email or password"}},
)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, form.username, form.password)
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    responses={
        401: {"description": "Invalid or expired token"},
        403: {"description": "Account is deactivated"},
    },
)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
