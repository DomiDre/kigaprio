import inspect
import json
import os
from datetime import datetime, timedelta
from typing import Any

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from kigaprio.services.magic_word import (
    DEFAULT_MAGIC_WORD,
    create_or_update_magic_word,
    get_magic_word_from_cache_or_db,
)
from kigaprio.services.redis_service import get_redis

router = APIRouter()
security = HTTPBearer()

POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")


class UpdateMagicWordRequest(BaseModel):
    new_magic_word: str = Field(..., min_length=4)


class AdminLoginRequest(BaseModel):
    identity: str  # email or username
    password: str


class AdminAuthResponse(BaseModel):
    token: str
    admin: dict[str, Any]


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Verify admin token and return admin data"""
    token = credentials.credentials

    # Check if token is cached
    cached_admin = await redis_client.get(f"admin_session:{token}")
    if cached_admin:
        return json.loads(cached_admin)

    # Verify with PocketBase
    try:
        async with httpx.AsyncClient() as client:
            # First, get admin data using the token
            response = await client.get(
                f"{POCKETBASE_URL}/api/admins/auth-refresh",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=401, detail="Invalid or expired admin token"
                )

            data = response.json()
            admin_data = data.get("admin", {})

            # Cache admin data for 15 minutes
            await redis_client.setex(
                f"admin_session:{token}", 900, json.dumps(admin_data)
            )

            return admin_data

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail="Authentication service unavailable"
        ) from e


@router.post("/login")
async def admin_login(
    request: AdminLoginRequest, redis_client: redis.Redis = Depends(get_redis)
) -> AdminAuthResponse:
    """Authenticate a PocketBase admin and return a token"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POCKETBASE_URL}/api/admins/auth-with-password",
                json={"identity": request.identity, "password": request.password},
            )

            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid admin credentials")

            data = response.json()
            token = data.get("token")
            admin = data.get("admin")

            # Cache admin session
            await redis_client.setex(
                f"admin_session:{token}",
                900,  # 15 minutes
                json.dumps(admin),
            )

            # Log admin login
            redis_client.hincrby(
                f"stats:admin_logins:{datetime.now().strftime('%Y%m%d')}",
                admin.get("email", "unknown"),
                1,
            )

            return AdminAuthResponse(token=token, admin=admin)

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail="Authentication service unavailable"
        ) from e


# ==================== Admin Protected Endpoints ====================
@router.get("/magic-word-info")
async def get_magic_word_info(
    redis_client: redis.Redis = Depends(get_redis),
    admin: dict[str, Any] = Depends(get_current_admin),
):
    """Admin endpoint to check current magic word settings"""

    try:
        magic_word = await get_magic_word_from_cache_or_db(redis_client)
        if not magic_word:
            magic_word = DEFAULT_MAGIC_WORD

        # Get statistics from Redis
        today = datetime.now().strftime("%Y%m%d")

        successful_raw = redis_client.hget(f"stats:registrations:{today}", "successful")
        if inspect.isawaitable(successful_raw):
            successful = await successful_raw
        else:
            successful = successful_raw

        failed_raw = redis_client.hget(f"stats:registrations:{today}", "failed")
        if inspect.isawaitable(failed_raw):
            failed = await failed_raw
        else:
            failed = failed_raw

        verifications_raw = redis_client.hget(
            f"stats:magic_word_success:{today}", "count"
        )
        if inspect.isawaitable(verifications_raw):
            verifications = await verifications_raw
        else:
            verifications = verifications_raw

        stats = {
            "registrations_today": {
                "successful": int(successful) if successful else 0,
                "failed": int(failed) if failed else 0,
            },
            "magic_word_verifications_today": int(verifications)
            if verifications
            else 0,
        }

        # Get last change info
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/system_settings/records",
                params={"filter": 'key="registration_magic_word"'},
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
            "statistics": stats,
            "admin_email": admin.get("email"),
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

    admin_email = admin.get("email", "unknown")
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


@router.get("/stats")
async def get_admin_stats(
    redis_client: redis.Redis = Depends(get_redis),
    admin: dict[str, Any] = Depends(get_current_admin),
):
    """Get registration and usage statistics"""

    # Get stats for the last 7 days
    stats = {}
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")

        successful_raw = redis_client.hget(f"stats:registrations:{date}", "successful")
        if inspect.isawaitable(successful_raw):
            successful = await successful_raw
        else:
            successful = successful_raw

        failed_raw = redis_client.hget(f"stats:registrations:{date}", "failed")
        if inspect.isawaitable(failed_raw):
            failed = await failed_raw
        else:
            failed = failed_raw

        verifications_raw = redis_client.hget(
            f"stats:magic_word_success:{date}", "count"
        )
        if inspect.isawaitable(verifications_raw):
            verifications = await verifications_raw
        else:
            verifications = verifications_raw

        day_stats = {
            "registrations": {
                "successful": int(successful) if successful else 0,
                "failed": int(failed) if failed else 0,
            },
            "magic_word_verifications": int(verifications) if verifications else 0,
        }

        stats[date] = day_stats

    return {"statistics": stats, "requested_by": admin.get("email")}


@router.get("/audit-log")
async def get_audit_log(
    redis_client: redis.Redis = Depends(get_redis),
    admin: dict[str, Any] = Depends(get_current_admin),
    days: int = 7,
):
    """Get audit log of magic word changes"""

    if days > 30:
        days = 30

    logs = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        pattern = f"audit:magic_word:{date}*"

        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)

            for key in keys:
                log_data = await redis_client.get(key)
                if log_data:
                    logs.append(json.loads(log_data))

            if cursor == 0:
                break

    # Sort by timestamp
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "audit_logs": logs[:100],  # Limit to 100 most recent
        "requested_by": admin.get("email"),
    }
