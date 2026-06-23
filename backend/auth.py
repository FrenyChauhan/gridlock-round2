"""
backend/auth.py
================
JWT authentication for Gridlock 2.0 Backend.

Hardcoded user store — no DB needed for prototype.
Token contains: user_id, role, region, team_id.
Token expiry: 8 hours (one shift).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# ------------------------------------------------------------------
# JWT SETTINGS
# ------------------------------------------------------------------
SECRET_KEY  = os.getenv("GRIDLOCK_SECRET", "gr1dl0ck-b3ng4luru-s3cr3t-k3y-2024")
ALGORITHM   = "HS256"
EXPIRE_HOURS = 8   # one patrol shift

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ------------------------------------------------------------------
# REGION MAPPING
# ------------------------------------------------------------------
REGION_STATIONS: dict[str, list[str]] = {
    "north"  : ["Malleshwaram", "Rajajinagar", "Magadi Road", "Jeevanbheemanagar"],
    "central": ["Upparpet", "Shivajinagar", "City Market", "Vijayanagara"],
    "east"   : ["HAL Old Airport", "Kodigehalli", "K.R. Pura",
                "Mahadevapura", "Chikkajala", "HSR Layout"],
    "all"    : [],   # superadmin — no station filter applied
}

# ------------------------------------------------------------------
# HARDCODED USER STORE
# ------------------------------------------------------------------
# Passwords are stored as bcrypt hashes.
# We hash them at module load time so startup is slower once but
# comparisons remain secure.

def _h(plain: str) -> str:
    return pwd_context.hash(plain)


_CONTROL_ROOM_USERS = [
    {
        "user_id"  : "cr_north",
        "email"    : "cr_north@blrtraffic.gov.in",
        "password" : _h("north123"),
        "role"     : "control_room",
        "region"   : "north",
        "team_id"  : None,
        "full_name": "North Control Room",
    },
    {
        "user_id"  : "cr_central",
        "email"    : "cr_central@blrtraffic.gov.in",
        "password" : _h("central123"),
        "role"     : "control_room",
        "region"   : "central",
        "team_id"  : None,
        "full_name": "Central Control Room",
    },
    {
        "user_id"  : "cr_east",
        "email"    : "cr_east@blrtraffic.gov.in",
        "password" : _h("east123"),
        "role"     : "control_room",
        "region"   : "east",
        "team_id"  : None,
        "full_name": "East Control Room",
    },
    {
        "user_id"  : "superadmin",
        "email"    : "superadmin@blrtraffic.gov.in",
        "password" : _h("admin123"),
        "role"     : "superadmin",
        "region"   : "all",
        "team_id"  : None,
        "full_name": "Super Administrator",
    },
]

# Generate T001–T040 officer accounts
_OFFICER_USERS = [
    {
        "user_id"  : f"officer_t{n:03d}",
        "email"    : f"officer_t{n:03d}@blrtraffic.gov.in",
        "password" : _h(f"cop{n:03d}"),
        "role"     : "officer",
        "region"   : None,     # officers see only their own team
        "team_id"  : f"T{n:03d}",
        "full_name": f"Patrol Officer T{n:03d}",
    }
    for n in range(1, 41)
]

ALL_USERS: dict[str, dict] = {
    u["email"]: u
    for u in (_CONTROL_ROOM_USERS + _OFFICER_USERS)
}


# ------------------------------------------------------------------
# AUTH HELPERS
# ------------------------------------------------------------------

def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Return user dict if credentials are valid, else None."""
    user = ALL_USERS.get(email)
    if not user:
        return None
    if not pwd_context.verify(password, user["password"]):
        return None
    return user


def create_access_token(user: dict) -> str:
    """Issue a JWT that expires in EXPIRE_HOURS hours."""
    expire = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    payload = {
        "sub"     : user["user_id"],
        "email"   : user["email"],
        "role"    : user["role"],
        "region"  : user["region"],
        "team_id" : user["team_id"],
        "exp"     : expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ------------------------------------------------------------------
# FASTAPI DEPENDENCIES
# ------------------------------------------------------------------

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency — returns decoded token payload."""
    return decode_token(token)


async def require_control_room(user: dict = Depends(get_current_user)) -> dict:
    """Allow control_room and superadmin only."""
    if user.get("role") not in ("control_room", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Control room access required.",
        )
    return user


async def require_superadmin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required.",
        )
    return user


async def require_officer(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "officer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officer access required.",
        )
    return user


def get_station_filter(user: dict) -> Optional[list[str]]:
    """
    Return list of stations this user can see, or None = no filter.
    Superadmin & 'all' region: no filter.
    Officers: filter by their assigned station (via team_id -> assignment).
    """
    role   = user.get("role")
    region = user.get("region")

    if role == "superadmin" or region == "all":
        return None   # see everything

    if role == "control_room":
        return REGION_STATIONS.get(region, [])

    return None   # officer filtering handled per-endpoint
