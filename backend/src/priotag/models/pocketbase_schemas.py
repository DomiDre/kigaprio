"""Pydantic models of schemas in pocketbase collections"""

from typing import Literal, Optional

from pydantic import BaseModel


class UsersResponse(BaseModel):
    """Response from pocketbase upon a request for entries from users collection"""

    id: str
    email: str | None = None
    emailVisibility: bool
    verified: bool
    username: str
    role: Literal["user", "service", "institution_admin", "super_admin"]
    admin_wrapped_dek: str
    user_wrapped_dek: str
    salt: str
    encrypted_fields: str
    institution_id: Optional[str] = None
    collectionId: str
    collectionName: str
    created: str
    updated: str
    lastSeen: str


class PriorityRecord(BaseModel):
    """Encrypted priority record (stored in database)."""

    id: str
    userId: str
    identifier: str
    month: str
    encrypted_fields: str
    manual: bool
    institution_id: Optional[str] = None
    collectionId: str
    collectionName: str
    created: str
    updated: str


class VacationDayRecord(BaseModel):
    """Vacation day record (stored in database)."""

    id: str
    date: str
    type: Literal["vacation", "admin_leave", "public_holiday"]
    description: str
    created_by: str
    institution_id: Optional[str] = None
    collectionId: str
    collectionName: str
    created: str
    updated: str


class InstitutionRecord(BaseModel):
    """Institution record (stored in database)."""

    id: str
    name: str
    short_code: str
    registration_magic_word: str
    admin_public_key: Optional[str] = None
    settings: dict = {}
    active: bool = True
    collectionId: str
    collectionName: str
    created: str
    updated: str
