import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Query

from kigaprio.models.auth import DEKData, TokenVerificationData
from kigaprio.models.pocketbase_schemas import PriorityRecord
from kigaprio.models.priorities import (
    PriorityRecordCore,
    PriorityResponse,
)
from kigaprio.models.request import SuccessResponse
from kigaprio.services.encryption import EncryptionManager
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import get_redis
from kigaprio.utils import get_dek_from_request, verify_token

router = APIRouter()


@router.get("", response_model=list[PriorityResponse])
async def get_user_priorities(
    month: str | None = Query(None, description="Filter by month (YYYY-MM)"),
    auth_data: TokenVerificationData = Depends(verify_token),
    dek_data: DEKData = Depends(get_dek_from_request),
):
    """Get all priorities for the authenticated user, optionally filtered by month."""

    user_id = auth_data.user.id
    token = auth_data.token

    # Build filter
    filter_parts = [f'userId = "{user_id}"']
    if month:
        filter_parts.append(f'month = "{month}"')
    filter_str = " && ".join(filter_parts)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": filter_str,
                    "sort": "-month",
                    "perPage": 100,  # Get all records
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Abrufen der Prioritäten",
                )

            data = response.json()
            items = data.get("items", [])

            # Decrypt each record
            decrypted_items = []
            for item in items:
                encrypted_record = PriorityRecord(**item)

                # Decrypt the weeks data
                decrypted_weeks = EncryptionManager.decrypt_fields(
                    encrypted_record.encrypted_fields,
                    dek_data.dek,
                )

                decrypted_items.append(
                    PriorityResponse(
                        id=encrypted_record.id,
                        userId=encrypted_record.userId,
                        month=encrypted_record.month,
                        weeks=decrypted_weeks["weeks"],
                        created=encrypted_record.created,
                        updated=encrypted_record.updated,
                    )
                )

            return decrypted_items

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.get("/{priority_id}", response_model=PriorityResponse)
async def get_priority(
    priority_id: str,
    auth_data: TokenVerificationData = Depends(verify_token),
    dek_data: DEKData = Depends(get_dek_from_request),
):
    """Get a specific priority record by ID."""

    user_id = auth_data.user.id
    token = auth_data.token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Priorität nicht gefunden",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Abrufen der Priorität",
                )

            encrypted_record = PriorityRecord(**response.json())

            # Verify ownership
            if encrypted_record.userId != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung für diese Priorität",
                )

            # Decrypt weeks data
            decrypted_weeks = EncryptionManager.decrypt_fields(
                encrypted_record.encrypted_fields,
                dek_data.dek,
            )

            return PriorityResponse(
                id=encrypted_record.id,
                userId=encrypted_record.userId,
                month=encrypted_record.month,
                weeks=decrypted_weeks["weeks"],
                created=encrypted_record.created,
                updated=encrypted_record.updated,
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.post("", response_model=SuccessResponse)
async def create_priority(
    priority: PriorityRecordCore,
    auth_data: TokenVerificationData = Depends(verify_token),
    dek_data: DEKData = Depends(get_dek_from_request),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Create a new priority record for the authenticated user."""

    user_id = auth_data.user.id
    token = auth_data.token

    # Check for duplicate month
    duplicate_check_key = f"priority_check:{user_id}:{priority.month}"
    if redis_client.exists(duplicate_check_key):
        raise HTTPException(
            status_code=429,
            detail="Eine Priorität für diesen Monat wird bereits verarbeitet",
        )

    # Set temporary lock (5 seconds)
    redis_client.setex(duplicate_check_key, 5, "creating")

    try:
        async with httpx.AsyncClient() as client:
            # Check if record already exists for this month
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{priority.month}"',
                },
            )

            if check_response.status_code == 200:
                existing = check_response.json()
                if existing.get("totalItems", 0) > 0:
                    raise HTTPException(
                        status_code=409,
                        detail="Eine Priorität für diesen Monat existiert bereits",
                    )

            # Encrypt the weeks data
            encrypted_data = EncryptionManager.encrypt_fields(
                {"weeks": [week.model_dump() for week in priority.weeks]},
                dek_data.dek,
            )

            # Create encrypted record
            encrypted_priority = {
                "userId": user_id,
                "month": priority.month,
                "encrypted_fields": encrypted_data,
            }

            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                json=encrypted_priority,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get(
                        "message", "Fehler beim Erstellen der Priorität"
                    ),
                )

            return SuccessResponse(message="Prioritaet erfolgreich angelegt")

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e
    finally:
        redis_client.delete(duplicate_check_key)


@router.patch("/{priority_id}", response_model=SuccessResponse)
async def update_priority(
    priority_id: str,
    priority: PriorityRecordCore,
    auth_data: TokenVerificationData = Depends(verify_token),
    dek_data: DEKData = Depends(get_dek_from_request),
):
    """Update an existing priority record."""

    user_id = auth_data.user.id
    token = auth_data.token

    try:
        async with httpx.AsyncClient() as client:
            # Verify record exists and belongs to user
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if check_response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Priorität nicht gefunden",
                )

            if check_response.status_code != 200:
                raise HTTPException(
                    status_code=check_response.status_code,
                    detail="Fehler beim Überprüfen der Priorität",
                )

            existing_data = PriorityRecord(**check_response.json())
            if existing_data.userId != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung für diese Priorität",
                )

            # Encrypt the updated weeks data
            encrypted_data = EncryptionManager.encrypt_fields(
                {"weeks": [week.model_dump() for week in priority.weeks]},
                dek_data.dek,
            )

            # Update with encrypted data
            encrypted_priority = {
                "userId": user_id,
                "month": priority.month,
                "encrypted_fields": encrypted_data,
            }

            response = await client.patch(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
                headers={"Authorization": f"Bearer {token}"},
                json=encrypted_priority,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get(
                        "message", "Fehler beim Aktualisieren der Priorität"
                    ),
                )

            return SuccessResponse(message="Prioritaet erfolgreich aktualisiert")

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.delete("/{priority_id}")
async def delete_priority(
    priority_id: str,
    auth_data: TokenVerificationData = Depends(verify_token),
):
    """Delete a priority record."""

    user_id = auth_data.user.id
    token = auth_data.token

    try:
        async with httpx.AsyncClient() as client:
            # Verify ownership
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if check_response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Priorität nicht gefunden",
                )

            if check_response.status_code == 200:
                existing_data = check_response.json()
                if existing_data["userId"] != user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="Keine Berechtigung für diese Priorität",
                    )

            # Delete the record
            response = await client.delete(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Löschen der Priorität",
                )

            return {"message": "Priorität erfolgreich gelöscht"}

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e
