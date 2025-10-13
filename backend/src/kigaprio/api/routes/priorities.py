import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException

from kigaprio.models.auth import DEKData, TokenVerificationData
from kigaprio.models.pocketbase_schemas import PriorityRecord
from kigaprio.models.priorities import (
    PriorityResponse,
    WeekPriority,
    validate_month_format_and_range,
)
from kigaprio.models.request import SuccessResponse
from kigaprio.services.encryption import EncryptionManager
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import get_redis
from kigaprio.utils import get_dek_from_request, verify_token

router = APIRouter()


@router.get("", response_model=list[PriorityResponse])
async def get_user_priorities(
    auth_data: TokenVerificationData = Depends(verify_token),
    dek_data: DEKData = Depends(get_dek_from_request),
):
    """Get all priorities for the authenticated user, optionally filtered by month."""

    user_id = auth_data.user.id
    token = auth_data.token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}"',
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
                        month=encrypted_record.month,
                        weeks=decrypted_weeks["weeks"],
                    )
                )

            return decrypted_items

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.get("/{month}", response_model=PriorityResponse)
async def get_priority(
    month: str,
    auth_data: TokenVerificationData = Depends(verify_token),
    dek_data: DEKData = Depends(get_dek_from_request),
):
    """Get a specific priority record by ID."""

    user_id = auth_data.user.id
    token = auth_data.token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}"',
                },
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

            items = response.json()["items"]
            if len(items) == 0:
                raise HTTPException(
                    status_code=400, detail="Priorität gefunden aber leer"
                )

            encrypted_record = PriorityRecord(**items[0])

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
                month=encrypted_record.month,
                weeks=decrypted_weeks["weeks"],
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.put("/{month}", response_model=SuccessResponse)
async def save_priority(
    month: str,
    weeks: list[WeekPriority],
    auth_data: TokenVerificationData = Depends(verify_token),
    dek_data: DEKData = Depends(get_dek_from_request),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Create or update a priority record for the authenticated user."""

    user_id = auth_data.user.id
    token = auth_data.token

    # Validate month
    try:
        validate_month_format_and_range(month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Check for duplicate month
    rate_limit_key = f"priority_check:{user_id}:{month}"
    if redis_client.exists(rate_limit_key):
        raise HTTPException(
            status_code=429,
            detail="Bitte warten Sie einen Moment",
        )

    redis_client.setex(rate_limit_key, 2, "saving")  # 2 sec lock

    try:
        async with httpx.AsyncClient() as client:
            # Check if record already exists for this month
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}"',
                },
            )

            existing = (
                check_response.json() if check_response.status_code == 200 else None
            )
            existing_id = None

            if existing and existing.get("totalItems", 0) > 0:
                existing_id = existing["items"][0]["id"]

            # Encrypt the weeks data
            encrypted_data = EncryptionManager.encrypt_fields(
                {"weeks": [week.model_dump() for week in weeks]},
                dek_data.dek,
            )

            # Create encrypted record
            encrypted_priority = {
                "userId": user_id,
                "month": month,
                "encrypted_fields": encrypted_data,
            }

            if existing_id:
                response = await client.patch(
                    f"{POCKETBASE_URL}/api/collections/priorities/records/{existing_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json=encrypted_priority,
                )
                message = "Priorität gespeichert"
            else:
                response = await client.post(
                    f"{POCKETBASE_URL}/api/collections/priorities/records",
                    headers={"Authorization": f"Bearer {token}"},
                    json=encrypted_priority,
                )
                message = "Priorität erstellt"

            if response.status_code not in [200, 201]:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message", "Fehler beim Speichern"),
                )

            return SuccessResponse(message=message)

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e
    finally:
        redis_client.delete(rate_limit_key)


@router.delete("/{month}")
async def delete_priority(
    month: str,
    auth_data: TokenVerificationData = Depends(verify_token),
):
    """Delete a priority record."""

    user_id = auth_data.user.id
    token = auth_data.token

    try:
        async with httpx.AsyncClient() as client:
            # Find record in database
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}"',
                },
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

            items = check_response.json()["items"]
            if len(items) == 0:
                raise HTTPException(
                    status_code=400, detail="Priorität gefunden aber leer"
                )

            record_id = items[0]["id"]

            # Delete the record
            response = await client.delete(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{record_id}",
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
