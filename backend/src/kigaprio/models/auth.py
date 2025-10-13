"""Pydantic models for auth routes"""

from typing import Literal

from pydantic import BaseModel, Field

from kigaprio.models.pocketbase_schemas import UsersResponse


class MagicWordRequest(BaseModel):
    magic_word: str = Field(..., min_length=1)


class MagicWordResponse(BaseModel):
    success: bool
    token: str | None = None
    message: str | None = None


class RegisterRequest(BaseModel):
    identity: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    passwordConfirm: str
    name: str = Field(..., min_length=1)
    registration_token: str


class DatabaseLoginResponse(BaseModel):
    """Response from pocketbase upon login request"""

    token: str
    record: UsersResponse


class LoginRequest(BaseModel):
    identity: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1)
    security_tier: Literal["balanced", "high", "convenience"] | None = None


class LoginResponse(BaseModel):
    """Response by fastapi upon a successful login request"""

    token: str
    message: str
    security_tier: Literal["high", "balanced", "convenience"]

    # For high and convenience modes
    dek: str | None = None

    # For balanced mode
    client_key_part: str | None = None


class SessionInfo(BaseModel):
    id: str
    username: str
    security_tier: Literal["high", "balanced", "convenience"]
    is_admin: bool


class TokenVerificationData(BaseModel):
    token: str
    new_token: str | None = None
    user: SessionInfo


class DEKData(BaseModel):
    dek: bytes
    user_id: str
    security_tier: str
