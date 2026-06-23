"""
backend/routers/auth_router.py
================================
POST /auth/login  — exchange credentials for JWT
GET  /auth/me     — return current user info
GET  /auth/users  — list all users (superadmin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    require_superadmin,
    ALL_USERS,
    EXPIRE_HOURS,
)
from backend.models import TokenResponse, UserInfo, LoginRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Login and get JWT token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    Standard OAuth2 password flow.
    Submit email as `username` and password in form body.
    Returns a Bearer JWT valid for one patrol shift (8 hours).
    """
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user)
    return TokenResponse(
        access_token = token,
        token_type   = "bearer",
        role         = user["role"],
        region       = user["region"],
        team_id      = user["team_id"],
        expires_in   = EXPIRE_HOURS * 3600,
    )


@router.post("/login/json", response_model=TokenResponse,
             summary="Login with JSON body (alternative to form)")
def login_json(body: LoginRequest):
    """Alternative login endpoint that accepts JSON instead of form data."""
    user = authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user)
    return TokenResponse(
        access_token = token,
        token_type   = "bearer",
        role         = user["role"],
        region       = user["region"],
        team_id      = user["team_id"],
        expires_in   = EXPIRE_HOURS * 3600,
    )


@router.get("/me", response_model=UserInfo, summary="Get current user profile")
def me(current_user: dict = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    email    = current_user.get("email", "")
    db_user  = ALL_USERS.get(email, {})
    return UserInfo(
        user_id   = current_user["sub"],
        email     = email,
        role      = current_user["role"],
        region    = current_user.get("region"),
        team_id   = current_user.get("team_id"),
        full_name = db_user.get("full_name", current_user["sub"]),
    )


@router.get("/users", summary="List all users (superadmin only)")
def list_users(admin: dict = Depends(require_superadmin)):
    """Returns all registered users (passwords excluded)."""
    return [
        {
            "user_id"  : u["user_id"],
            "email"    : u["email"],
            "role"     : u["role"],
            "region"   : u["region"],
            "team_id"  : u["team_id"],
            "full_name": u["full_name"],
        }
        for u in ALL_USERS.values()
    ]
