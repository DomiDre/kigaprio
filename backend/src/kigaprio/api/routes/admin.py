import base64
import json
from typing import Any

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kigaprio.models.admin import (
    UpdateMagicWordRequest,
    UserPriorityRecordForAdmin,
)
from kigaprio.models.pocketbase_schemas import PriorityRecord, UsersResponse
from kigaprio.services.magic_word import (
    create_or_update_magic_word,
    get_magic_word_from_cache_or_db,
)
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import get_redis

router = APIRouter()
security = HTTPBearer()


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Check if token is in redis cache and of an admin, otherwise verify with PocketBase"""

    token = credentials.credentials
    session_key = f"session:{token}"

    # First, try to get session from Redis cache
    session_data = redis_client.get(session_key)

    if session_data:
        # Session found in cache
        user_data = json.loads(str(session_data))

        # Check if user is admin
        if not user_data.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Admin access required")

        # Return admin data in expected format
        return {
            "token": token,
            "user": {
                "id": user_data["id"],
                "username": user_data["username"],
            },
        }

    # Session not in cache
    try:
        async with httpx.AsyncClient() as client:
            # First, just check if the token is valid by making a simple request
            test_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records",
                params={"perPage": 1, "fields": "id"},
                headers={"Authorization": f"Bearer {token}"},
            )

            if test_response.status_code == 401:
                # Token is invalid or expired
                raise HTTPException(
                    status_code=401, detail="Session expired or invalid"
                )

            if test_response.status_code != 200:
                raise HTTPException(
                    status_code=503, detail="Unable to verify authentication"
                )

            # Token is valid. Now we need to determine if this is an admin.
            # We'll decode the JWT token to get the user ID
            # PocketBase tokens are JWT tokens with the user ID in the payload
            try:
                # JWT structure: header.payload.signature
                # We just need the payload
                parts = token.split(".")
                if len(parts) != 3:
                    raise ValueError("Invalid token format")

                # Decode payload (add padding if necessary)
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)  # Add padding
                decoded_payload = base64.urlsafe_b64decode(payload)
                token_data = json.loads(decoded_payload)

                user_id = token_data.get("id")
                if not user_id:
                    raise ValueError("No user ID in token")

                # Now fetch the specific user's data to check their role
                user_response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )

                if user_response.status_code != 200:
                    raise HTTPException(
                        status_code=401, detail="Unable to fetch user data"
                    )

                user_record = user_response.json()
                is_admin = user_record.get("role") == "admin"

                if not is_admin:
                    # Non-admin user - just deny access, don't modify anything
                    raise HTTPException(status_code=403, detail="Admin access required")

                # Admin user - safe to recreate session in cache
                session_info = {
                    "id": user_record["id"],
                    "username": user_record["username"],
                    "is_admin": True,
                    "type": "superuser",
                }

                # Store with admin TTL (15 minutes)
                redis_client.setex(
                    session_key,
                    900,  # 15 min for admin
                    json.dumps(session_info),
                )

                return {
                    "token": token,
                    "user": {
                        "id": user_record["id"],
                        "username": user_record["username"],
                    },
                }

            except (ValueError, KeyError, json.JSONDecodeError) as e:
                # Can't decode token - fall back to denying access
                raise HTTPException(
                    status_code=401, detail="Invalid token format"
                ) from e

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503, detail="Authentication service unavailable"
        ) from e


@router.get("/magic-word-info")
async def get_magic_word_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(get_redis),
    admin: dict[str, Any] = Depends(get_current_admin),
):
    """Admin endpoint to check current magic word settings"""

    try:
        magic_word = await get_magic_word_from_cache_or_db(redis_client)
        if not magic_word:
            raise HTTPException(
                status_code=500, detail="No magic word initialized on database"
            )

        async with httpx.AsyncClient() as client:
            token = credentials.credentials
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/system_settings/records",
                params={"filter": 'key="registration_magic_word"'},
                headers={"Authorization": f"Bearer {token}"},
            )

            last_updated = None
            last_updated_by = None

            if response.status_code == 200:
                data = response.json()
                if data.get("items") and len(data["items"]) > 0:
                    record = data["items"][0]
                    last_updated = record.get("updated")
                    last_updated_by = record.get("last_updated_by")

        return {
            "current_magic_word": magic_word,
            "last_updated": last_updated,
            "last_updated_by": last_updated_by,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/update-magic-word")
async def update_magic_word(
    request: UpdateMagicWordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(get_redis),
    admin: dict[str, Any] = Depends(get_current_admin),
):
    """Admin endpoint to update the magic word"""

    admin_id = admin["user"]["username"]
    admin_token = credentials.credentials

    success = await create_or_update_magic_word(
        request.new_magic_word, admin_token, redis_client, admin_id
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update magic word")

    return {
        "success": True,
        "message": "Magic word updated successfully",
        "updated_by": admin_id,
    }


@router.get("/users/{month}")
async def get_user_submissions(
    month: str,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> list[UserPriorityRecordForAdmin]:
    """Get all user submissions for a specific month, data is still
    encrypted and needs to be decrypted locally using admin private key
    and respective admin_wrapped_deks
    """

    token = admin["token"]
    async with httpx.AsyncClient() as client:
        # Fetch regular users (not superusers)
        users_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/users/records",
            params={"perPage": 500},
            headers={"Authorization": f"Bearer {token}"},
        )

        if users_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen der Benutzer"
            )

        users: list[UsersResponse] = [
            UsersResponse(**x) for x in users_response.json().get("items", [])
        ]

        # Fetch priorities for the month (of all users)
        priorities_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={"filter": f"month='{month}'", "perPage": 500},
            headers={"Authorization": f"Bearer {token}"},
        )

        if priorities_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen der Prioritäten"
            )

        priorities: list[PriorityRecord] = [
            PriorityRecord(**x) for x in priorities_response.json().get("items", [])
        ]

        # Make priorities be lookupable by user
        user_priorities: dict[str, PriorityRecord] = {}
        for priority in priorities:
            user_id = priority.userId
            if user_id in user_priorities:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ein Nutzer hat mehrere Prio Eintragungen für den Monat {month}. Dies sollte nicht passieren. Bitte melden zur Prüfung",
                )
            user_priorities[user_id] = priority

        # Build user submission list
        user_submissions = []
        for user in users:
            user_id = user.id
            priority = user_priorities.get(user_id)
            if priority is None:
                # user did not submit anything to priorities
                continue

            user_submissions.append(
                UserPriorityRecordForAdmin(
                    adminWrappedDek=user.admin_wrapped_dek,
                    userName=user.username,
                    month=priority.month,
                    userEncryptedFields=user.encrypted_fields,
                    prioritiesEncryptedFields=priority.encrypted_fields,
                )
            )

        return user_submissions


@router.get("/users/info/{user_id}")
async def get_user_for_admin(
    user_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),  # Your auth dependency
):
    """
    Return encrypted user data.
    Server CANNOT decrypt this - admin must decrypt client-side!
    """
    token = admin["token"]
    async with httpx.AsyncClient() as client:
        try:
            # Fetch user details
            user_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/users/records",
                params={"filter": f"username='{user_id}'"},
                headers={"Authorization": f"Bearer {token}"},
            )
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Fehler beim Abrufen des Benutzer"
                )
            response_data = user_response.json()
            if "items" not in response_data or "totalItems" not in response_data:
                raise HTTPException(
                    status_code=500, detail="In Antwort fehlen erwartete Felder"
                )
            if response_data["totalItems"] != 1:
                raise HTTPException(status_code=204, detail="User nicht gefunden")

            user_record = UsersResponse(**response_data["items"][0])
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="Unbekannter Fehler beim abrufen des Benutzer"
            ) from e

    return {
        "username": user_record.username,
        "admin_wrapped_dek": user_record.admin_wrapped_dek,  # RSA encrypted
        "encrypted_fields": user_record.encrypted_fields,
        "created": user_record.created,
    }
