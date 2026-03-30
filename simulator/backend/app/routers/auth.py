"""
Authentication router — /api/auth/signup, /api/auth/signin, /api/auth/me
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
import bcrypt

from app import auth_db
from app.jwt_utils import create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Password hashing helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ── Request / Response Models ────────────────────────────────────────────

class SignUpRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=1, le=150)
    phone_number: str = Field(..., min_length=1, max_length=20)
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=6, max_length=128)


class SignInRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    id: int
    name: str
    age: int | None
    phone_number: str | None
    email: str
    role: str


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignUpRequest):
    """Register a new user account."""
    # Check if email already exists
    existing = auth_db.fetch_one(
        "SELECT id FROM users WHERE email = %s", (body.email,)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Hash password
    password_hash = hash_password(body.password)

    # Insert user
    auth_db.execute(
        """INSERT INTO users (name, age, phone_number, email, password_hash, role)
           VALUES (%s, %s, %s, %s, %s, 'user')""",
        (body.name, body.age, body.phone_number, body.email, password_hash),
    )

    # Fetch the newly created user
    user = auth_db.fetch_one(
        "SELECT id, name, age, phone_number, email, role FROM users WHERE email = %s",
        (body.email,),
    )

    # Create JWT
    token = create_access_token({
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    })

    return {
        "token": token,
        "user": user,
    }


@router.post("/signin", response_model=AuthResponse)
def signin(body: SignInRequest):
    """Sign in with email and password."""
    # Look up user
    user = auth_db.fetch_one(
        "SELECT id, name, age, phone_number, email, password_hash, role FROM users WHERE email = %s",
        (body.email,),
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create JWT
    token = create_access_token({
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    })

    # Remove password_hash from response
    user_data = {k: v for k, v in user.items() if k != "password_hash"}

    return {
        "token": token,
        "user": user_data,
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Get the current authenticated user's info."""
    user = auth_db.fetch_one(
        "SELECT id, name, age, phone_number, email, role FROM users WHERE id = %s",
        (current_user["user_id"],),
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
