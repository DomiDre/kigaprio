import base64
import json
from datetime import datetime
from io import BytesIO
from typing import Any, cast

import httpx
import pandas as pd
import redis
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pandas.core.generic import WriteExcelBuffer

from kigaprio.models.admin import (
    MonthStatsResponse,
    ReminderRequest,
    ReminderResponse,
    UpdateMagicWordRequest,
    UserSubmissionResponse,
)
from kigaprio.models.pocketbase_schemas import UsersResponse
from kigaprio.models.priorities import PriorityResponse
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
                "email": user_data["email"],
                "name": user_data["name"],
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
                    "email": user_record["email"],
                    "name": user_record["name"],
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
                        "email": user_record["email"],
                        "name": user_record["name"],
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
            "admin_email": admin["user"]["email"],
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

    admin_email = admin["user"]["email"]
    admin_token = credentials.credentials

    success = await create_or_update_magic_word(
        request.new_magic_word, admin_token, redis_client, admin_email
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update magic word")

    return {
        "success": True,
        "message": "Magic word updated successfully",
        "updated_by": admin_email,
    }


@router.get("/stats/{month}")
async def get_month_stats(
    month: str,  # Format: YYYY-MM
    admin: dict[str, Any] = Depends(get_current_admin),
) -> MonthStatsResponse:
    """Get statistics for a specific month."""

    token = admin["token"]
    async with httpx.AsyncClient() as client:
        # Fetch all priority records for the month
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={"filter": f"month='{month}'", "perPage": 500},
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Fehler beim Abrufen der Daten")

        data = response.json()
        records = data.get("items", [])

        # Calculate statistics (same logic as before)
        unique_users = set()
        weekly_stats = {}
        completed_weeks = 0
        pending_weeks = 0

        for record in records:
            unique_users.add(record["userId"])
            week_num = record["weekNumber"]

            if week_num not in weekly_stats:
                weekly_stats[week_num] = {"completed": 0, "total": 0}

            weekly_stats[week_num]["total"] += 1

            priorities = record.get("priorities", {})
            valid_priorities = [p for p in priorities.values() if p is not None]

            if len(valid_priorities) == 5 and len(set(valid_priorities)) == 5:
                weekly_stats[week_num]["completed"] += 1
                completed_weeks += 1
            else:
                pending_weeks += 1

        weekly_completion = [
            {"week": week, "completed": stats["completed"], "total": stats["total"]}
            for week, stats in sorted(weekly_stats.items())
        ]

        return MonthStatsResponse(
            totalSubmissions=len(records),
            completedWeeks=completed_weeks,
            pendingWeeks=pending_weeks,
            uniqueUsers=len(unique_users),
            weeklyCompletion=weekly_completion,
        )


@router.get("/users/{month}")
async def get_user_submissions(
    month: str,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> list[UserSubmissionResponse]:
    """Get all user submissions for a specific month."""

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

        # Fetch priorities for the month
        priorities_response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={"filter": f"month='{month}'", "perPage": 500},
            headers={"Authorization": f"Bearer {token}"},
        )

        if priorities_response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Fehler beim Abrufen der Prioritäten"
            )

        priorities: list[PriorityResponse] = [
            PriorityResponse(**x) for x in priorities_response.json().get("items", [])
        ]

        # Group priorities by user
        user_priorities: dict[str, list[PriorityResponse]] = {}
        for priority in priorities:
            user_id = priority.userId
            if user_id not in user_priorities:
                user_priorities[user_id] = []
            user_priorities[user_id].append(priority)

        # Build user submission list
        user_submissions = []
        for user in users:
            user_id = user.id
            user_records = user_priorities.get(user_id, [])

            completed_weeks = 0
            last_activity = None

            for record in user_records:
                priorities_dict = record.priorities
                valid_priorities = [
                    p for p in priorities_dict.values() if p is not None
                ]

                if len(valid_priorities) == 5 and len(set(valid_priorities)) == 5:
                    completed_weeks += 1

                updated = record.updated
                if updated and (not last_activity or updated > last_activity):
                    last_activity = updated

            # TODO: this is dependent on the month that is being looked at
            total_weeks = 5  # Assuming 4 weeks per month

            if completed_weeks == total_weeks:
                status = "complete"
            elif completed_weeks > 0:
                status = "partial"
            else:
                status = "none"

            user_submissions.append(
                UserSubmissionResponse(
                    userId=user_id,
                    userName=user.name,
                    email=user.email,
                    completedWeeks=completed_weeks,
                    totalWeeks=total_weeks,
                    lastActivity=last_activity or datetime.now().isoformat(),
                    status=status,
                )
            )

        return user_submissions


@router.get("/export/{month}")
async def export_month_data(
    month: str,
    admin: dict[str, Any] = Depends(get_current_admin),
):
    """Export all priority data for a month as Excel file."""

    token = admin["token"]
    async with httpx.AsyncClient() as client:
        # Fetch all data with expanded user information
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/priorities/records",
            params={"filter": f"month='{month}'", "expand": "userId", "perPage": 500},
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Fehler beim Abrufen der Daten")

        data = response.json()
        records = data.get("items", [])

        # Prepare data for Excel
        rows = []
        for record in records:
            user = record.get("expand", {}).get("userId", {})
            priorities = record.get("priorities", {})

            row = {
                "Benutzer": user.get("name", "Unknown"),
                "E-Mail": user.get("email", ""),
                "Woche": record.get("weekNumber", ""),
                "Start": record.get("startDate", ""),
                "Ende": record.get("endDate", ""),
                "Montag": priorities.get("monday"),
                "Dienstag": priorities.get("tuesday"),
                "Mittwoch": priorities.get("wednesday"),
                "Donnerstag": priorities.get("thursday"),
                "Freitag": priorities.get("friday"),
                "Status": "Vollständig"
                if all(priorities.values())
                else "Unvollständig",
                "Zuletzt aktualisiert": record.get("updated", record.get("created")),
            }
            rows.append(row)

        # Create Excel file
        df = pd.DataFrame(rows)

        buffer = BytesIO()
        with pd.ExcelWriter(
            cast(WriteExcelBuffer, buffer), engine="openpyxl"
        ) as writer:
            df.to_excel(writer, sheet_name=f"Prioritäten {month}", index=False)

            # Add summary sheet
            summary_df = pd.DataFrame(
                [
                    {"Metrik": "Gesamteinträge", "Wert": len(records)},
                    {
                        "Metrik": "Eindeutige Benutzer",
                        "Wert": df["Benutzer"].nunique() if not df.empty else 0,
                    },
                    {
                        "Metrik": "Vollständige Wochen",
                        "Wert": (df["Status"] == "Vollständig").sum()
                        if not df.empty
                        else 0,
                    },
                    {
                        "Metrik": "Unvollständige Wochen",
                        "Wert": (df["Status"] == "Unvollständig").sum()
                        if not df.empty
                        else 0,
                    },
                ]
            )
            summary_df.to_excel(writer, sheet_name="Zusammenfassung", index=False)

        buffer.seek(0)

        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=prioritaeten_{month}.xlsx"
            },
        )


@router.post("/reminders")
async def send_reminders(
    request: ReminderRequest,
    admin: dict[str, Any] = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(get_redis),
) -> ReminderResponse:
    """Send email reminders to selected users."""

    token = admin["token"]
    results = []
    sent_count = 0
    failed_count = 0

    async with httpx.AsyncClient() as client:
        for user_id in request.userIds:
            try:
                # Fetch user details
                user_response = await client.get(
                    f"{POCKETBASE_URL}/api/collections/users/records/{user_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )

                if user_response.status_code != 200:
                    results.append(
                        {
                            "userId": user_id,
                            "email": "unknown",
                            "status": "failed",
                            "error": "Benutzer nicht gefunden",
                        }
                    )
                    failed_count += 1
                    continue

                user = user_response.json()

                # Here you would queue the email sending
                # For now, just log the action
                results.append(
                    {"userId": user_id, "email": user["email"], "status": "sent"}
                )
                sent_count += 1

            except Exception as e:
                results.append(
                    {
                        "userId": user_id,
                        "email": "unknown",
                        "status": "failed",
                        "error": str(e),
                    }
                )
                failed_count += 1

    # Log admin action
    log_key = f"admin_log:{admin.get('id')}:{datetime.now().isoformat()}"
    redis_client.setex(
        log_key,
        30 * 24 * 3600,  # Keep logs for 30 days
        json.dumps(
            {
                "action": "send_reminders",
                "admin_email": admin.get("email"),
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "recipients": len(request.userIds),
                    "sent": sent_count,
                    "failed": failed_count,
                    "month": request.month,
                },
            }
        ),
    )

    return ReminderResponse(sent=sent_count, failed=failed_count, details=results)
