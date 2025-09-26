import os

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from kigaprio.services.redis_service import get_redis
from kigaprio.utils import verify_token

router = APIRouter()

# Configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")


class Priority(BaseModel):
    id: int
    name: str
    color: str


class DayPriorities(BaseModel):
    monday: int | None = None
    tuesday: int | None = None
    wednesday: int | None = None
    thursday: int | None = None
    friday: int | None = None


class PriorityRecord(BaseModel):
    userId: str
    month: str
    weekNumber: int
    priorities: DayPriorities
    startDate: str
    endDate: str


class PriorityResponse(BaseModel):
    id: str
    userId: str
    month: str
    weekNumber: int
    priorities: dict
    startDate: str
    endDate: str
    created: str
    updated: str


@router.get("", response_model=list[PriorityResponse])
async def get_user_priorities(
    month: str | None = Query(None, description="Filter by month (YYYY-MM)"),
    auth_data: dict = Depends(verify_token),
):
    """Get all priorities for the authenticated user, optionally filtered by month."""

    user_id = auth_data["user"]["id"]
    token = auth_data["token"]

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
                    "sort": "weekNumber",
                    "perPage": 100,  # Get all records
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Fehler beim Abrufen der Prioritäten",
                )

            data = response.json()
            return data.get("items", [])

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.get("/{priority_id}", response_model=PriorityResponse)
async def get_priority(
    priority_id: str,
    auth_data: dict = Depends(verify_token),
):
    """Get a specific priority record by ID."""

    user_id = auth_data["user"]["id"]
    token = auth_data["token"]

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

            data = response.json()

            # Verify ownership
            if data["userId"] != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung für diese Priorität",
                )

            return data

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e


@router.post("", response_model=PriorityResponse)
async def create_priority(
    priority: PriorityRecord,
    auth_data: dict = Depends(verify_token),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Create a new priority record for the authenticated user."""

    user_id = auth_data["user"]["id"]
    token = auth_data["token"]

    # Ensure userId matches authenticated user
    priority.userId = user_id

    # Check for duplicate (same user, month, week)
    duplicate_check_key = (
        f"priority_check:{user_id}:{priority.month}:{priority.weekNumber}"
    )
    if redis_client.exists(duplicate_check_key):
        raise HTTPException(
            status_code=429,
            detail="Eine Priorität für diese Woche wird bereits verarbeitet",
        )

    # Set temporary lock (5 seconds)
    redis_client.setex(duplicate_check_key, 5, "creating")

    try:
        async with httpx.AsyncClient() as client:
            # First check if record already exists
            check_response = await client.get(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "filter": f'userId = "{user_id}" && month = "{priority.month}" && weekNumber = {priority.weekNumber}',
                },
            )

            if check_response.status_code == 200:
                existing = check_response.json()
                if existing.get("totalItems", 0) > 0:
                    raise HTTPException(
                        status_code=409,
                        detail="Eine Priorität für diese Woche existiert bereits",
                    )

            # Create new record
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/priorities/records",
                headers={"Authorization": f"Bearer {token}"},
                json=priority.model_dump(),
            )

            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get(
                        "message", "Fehler beim Erstellen der Priorität"
                    ),
                )

            return response.json()

    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail="Verbindungsfehler zum Datenbankserver",
        ) from e
    finally:
        redis_client.delete(duplicate_check_key)


@router.patch("/{priority_id}", response_model=PriorityResponse)
async def update_priority(
    priority_id: str,
    priority: PriorityRecord,
    auth_data: dict = Depends(verify_token),
):
    """Update an existing priority record."""

    user_id = auth_data["user"]["id"]
    token = auth_data["token"]

    # Ensure userId matches authenticated user
    priority.userId = user_id

    try:
        # First, verify the record exists and belongs to the user
        async with httpx.AsyncClient() as client:
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

            existing_data = check_response.json()
            if existing_data["userId"] != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Keine Berechtigung für diese Priorität",
                )

            # Update the record
            response = await client.patch(
                f"{POCKETBASE_URL}/api/collections/priorities/records/{priority_id}",
                headers={"Authorization": f"Bearer {token}"},
                json=priority.model_dump(),
            )

            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get(
                        "message", "Fehler beim Aktualisieren der Priorität"
                    ),
                )

            return response.json()

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
    auth_data: dict = Depends(verify_token),
):
    """Delete a priority record."""

    user_id = auth_data["user"]["id"]
    token = auth_data["token"]

    try:
        async with httpx.AsyncClient() as client:
            # First, verify ownership
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
