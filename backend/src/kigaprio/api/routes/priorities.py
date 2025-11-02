import httpx
import redis
from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException

from kigaprio.middleware.metrics import (
    track_data_operation,
    track_encryption_error,
    track_priority_submission,
)
from kigaprio.models.auth import SessionInfo
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
from kigaprio.utils import get_current_dek, get_current_token, verify_token

router = APIRouter()


@router.get("", response_model=list[PriorityResponse])
async def get_user_priorities(
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
):
    """Get all priorities for the authenticated user, optionally filtered by month."""

    user_id = auth_data.id

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && identifier = null',
                    "sort": "-month",
                    "perPage": 100,  # Get all records
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Abrufen der PrioritÃ¤ten",
                )

            data = response.json()
            items = data.get("items", [])

            # Decrypt each record
            decrypted_items = []
            for item in items:
                encrypted_record = PriorityRecord(**item)

                # Decrypt the weeks data
                try:
                    decrypted_weeks = EncryptionManager.decrypt_fields(
                        encrypted_record.encrypted_fields,
                        dek,
                    )
                except InvalidTag as e:
                    raise HTTPException(
                        status_code=500,
                        detail="Entschluesselung der Daten fehlgeschlagen",
                    ) from e

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
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
):
    """Get a specific priority record by ID."""

    user_id = auth_data.id

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}" && identifier = null',
                },
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="PrioritÃ¤t nicht gefunden",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Abrufen der PrioritÃ¤t",
                )

            items = response.json()["items"]
            if len(items) == 0:
                # no records found
                return PriorityResponse(month=month, weeks=[])

            encrypted_record = PriorityRecord(**items[0])

            # Verify ownership
            if encrypted_record.userId != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung fÃ¼r diese PrioritÃ¤t",
                )

            track_data_operation("read", "priorities")

            # Decrypt weeks data
            try:
                decrypted_weeks = EncryptionManager.decrypt_fields(
                    encrypted_record.encrypted_fields,
                    dek,
                )
            except InvalidTag as e:
                track_encryption_error("decrypt")
                raise HTTPException(
                    status_code=500,
                    detail="Entschluesselung der Daten fehlgeschlagen",
                ) from e
            except Exception:
                track_encryption_error("decrypt")
                raise

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
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
    dek: bytes = Depends(get_current_dek),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Create or update a priority record for the authenticated user."""

    user_id = auth_data.id

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
            # Check if record already exists for this month (for regular users, identifier is null)
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}" && identifier = null',
                },
            )

            existing = (
                check_response.json() if check_response.status_code == 200 else None
            )
            existing_id = None

            if existing and existing.get("totalItems", 0) > 0:
                existing_id = existing["items"][0]["id"]

            # Encrypt the weeks data
            try:
                encrypted_data = EncryptionManager.encrypt_fields(
                    {"weeks": [week.model_dump() for week in weeks]},
                    dek,
                )
            except Exception as e:
                track_encryption_error("encrypt")
                raise HTTPException(
                    status_code=500,
                    detail="VerschlÃ¼sselung der Daten fehlgeschlagen",
                ) from e

            # Create encrypted record (identifier remains null for regular users)
            encrypted_priority = {
                "userId": user_id,
                "month": month,
                "encrypted_fields": encrypted_data,
                "identifier": None,  # Regular users always have identifier=null
            }

            track_priority_submission(month)
            if existing_id:
                track_data_operation("update", "priorities")
                response = await client.patch(
                    f"{POCKETBASE_URL}/api/collections/priorities/records/{existing_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json=encrypted_priority,
                )
                message = "PrioritÃ¤t gespeichert"
            else:
                track_data_operation("create", "priorities")
                response = await client.post(
                    f"{POCKETBASE_URL}/api/collections/priorities/records",
                    headers={"Authorization": f"Bearer {token}"},
                    json=encrypted_priority,
                )
                message = "PrioritÃ¤t erstellt"

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
    auth_data: SessionInfo = Depends(verify_token),
    token: str = Depends(get_current_token),
):
    """Delete a priority record."""

    user_id = auth_data.id

    try:
        async with httpx.AsyncClient() as client:
            # Find record in database (regular users have identifier=null)
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{month}" && identifier = null',
                },
            )

            if check_response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="PrioritÃ¤t nicht gefunden",
                )

            if check_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Fehler bei dem Versuch die PrioritÃ¤t zu lÃ¶schen.",
                )

            items = check_response.json()["items"]
            if len(items) == 0:
                raise HTTPException(
                    status_code=400, detail="PrioritÃ¤t gefunden aber leer"
                )
            record = items[0]
            if record["userId"] != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung fÃ¼r diese PrioritÃ¤t",
                )

            record_id = record["id"]

            # Delete the record
            response = await client.delete(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{record_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim LÃ¶schen der PrioritÃ¤t",
                )

            return {"message": "PrioritÃ¤t erfolgreich gelÃ¶scht"}

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e
