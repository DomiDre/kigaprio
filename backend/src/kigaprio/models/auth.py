"""Pydantic models for auth routes"""

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


class LoginResponse(BaseModel):
    """Response by fastapi upon a successful login request"""

    token: str
    message: str
