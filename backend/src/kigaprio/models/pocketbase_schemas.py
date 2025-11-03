"""Pydantic models of schemas in pocketbase collections"""

from typing import Literal

from pydantic import BaseModel


class UsersResponse(BaseModel):
    """Response from pocketbase upon a request for entries from users collection"""

    id: str
    email: str | None = None
    emailVisibility: bool
    verified: bool
    username: str
    role: Literal["user", "service", "admin", "generic"]
    admin_wrapped_dek: str
    user_wrapped_dek: str
    salt: str
    encrypted_fields: str
    collectionId: str
    collectionName: str
    created: str
    updated: str


class PriorityRecord(BaseModel):
    """Encrypted priority record (stored in database)."""

    id: str
    userId: str
    identifier: str
    month: str
    encrypted_fields: str
    manual: bool
    collectionId: str
    collectionName: str
    created: str
    updated: str
