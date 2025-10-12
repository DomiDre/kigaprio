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
    role: Literal["user"] | Literal["service"] | Literal["admin"] | Literal["generic"]
    admin_wrapped_dek: str
    user_wrapped_dek: str
    salt: str
    encrypted_fields: str
    collectionId: str
    collectionName: str
    created: str
    updated: str
    security_tier: Literal["balanced"] | Literal["high"] | Literal["convenience"]
