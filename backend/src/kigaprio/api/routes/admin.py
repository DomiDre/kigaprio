import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException

from kigaprio.models.admin import (
    UpdateMagicWordRequest,
    UserPriorityRecordForAdmin,
)
from kigaprio.models.auth import SessionInfo
from kigaprio.models.pocketbase_schemas import PriorityRecord, UsersResponse
from kigaprio.services.magic_word import (
    create_or_update_magic_word,
    get_magic_word_from_cache_or_db,
)
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import get_redis
from kigaprio.utils import get_current_token, require_admin

router = APIRouter()


@router.get("/magic-word-info")
async def get_magic_word_info(
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Admin endpoint to check current magic word settings"""

    try:
        magic_word = await get_magic_word_from_cache_or_db(redis_client)
        if not magic_word:
            raise HTTPException(
                status_code=500, detail="No magic word initialized on database"
            )

        async with httpx.AsyncClient() as client:
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
    token: str = Depends(get_current_token),
    session_info: SessionInfo = Depends(require_admin),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Admin endpoint to update the magic word"""

    admin_id = session_info.username

    success = await create_or_update_magic_word(
        request.new_magic_word, token, redis_client, admin_id
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
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
) -> list[UserPriorityRecordForAdmin]:
    """Get all user submissions for a specific month, data is still
    encrypted and needs to be decrypted locally using admin private key
    and respective admin_wrapped_deks
    """

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
            if user_id not in user_priorities:
                # user did not submit anything to priorities
                continue

            priority = user_priorities[user_id]

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
    token: str = Depends(get_current_token),
    _=Depends(require_admin),
):
    """
    Return encrypted user data.
    Server CANNOT decrypt this - admin must decrypt client-side!
    """
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
