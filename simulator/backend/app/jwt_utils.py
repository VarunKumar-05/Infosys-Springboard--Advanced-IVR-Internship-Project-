"""
JWT utility functions for token creation and validation.
"""

from __future__ import annotations
import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status


# ── Configuration ────────────────────────────────────────────────────────

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-!@#$%")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


# ── Token Creation ───────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    """
    Create a signed JWT token.
    `data` should contain at least: user_id, email, name, role
    """
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ── Token Validation ─────────────────────────────────────────────────────

def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency — extracts the JWT from the Authorization header,
    validates it, and returns the decoded payload.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = auth_header.split(" ", 1)[1]
    return decode_token(token)


def require_role(role: str):
    """
    Dependency factory — returns a FastAPI dependency that checks
    if the current user has the required role.
    """
    def dependency(request: Request) -> dict:
        user = get_current_user(request)
        if user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return user
    return dependency
