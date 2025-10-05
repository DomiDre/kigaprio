import os

import httpx
import redis
from fastapi import HTTPException

from kigaprio.services.pocketbase_service import POCKETBASE_URL

SERVICE_ACCOUNT_EMAIL = os.getenv("PB_SERVICE_EMAIL")
SERVICE_ACCOUNT_PASSWORD = os.getenv("PB_SERVICE_PASSWORD")


async def get_magic_word_from_cache_or_db(redis_client: redis.Redis) -> str | None:
    """Get magic word from Redis cache or database"""
    # Try cache first
    cached_word = redis_client.get("magic_word:current")
    if cached_word:
        return (
            cached_word.decode("utf-8")
            if isinstance(cached_word, bytes)
            else str(cached_word)
        )

    # Fetch from database
    try:
        async with httpx.AsyncClient() as client:
            # Use PocketBase's public API to get system settings
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
                json={
                    "identity": SERVICE_ACCOUNT_EMAIL,
                    "password": SERVICE_ACCOUNT_PASSWORD,
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=401, detail="Invalid service credentials"
                )

            data = response.json()
            service_token = data.get("token")
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/system_settings/records",
                params={"filter": 'key="registration_magic_word"'},
                headers={"Authorization": f"Bearer {service_token}"},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("items") and len(data["items"]) > 0:
                    magic_word = data["items"][0]["value"]
                    # Cache for 5 minutes
                    redis_client.setex("magic_word:current", 300, magic_word)
                    return magic_word
    except Exception as e:
        print(f"Error fetching magic word from database: {e}")

    return None


async def create_or_update_magic_word(
    new_word: str,
    admin_token: str,
    redis_client: redis.Redis,
    admin_email: str = "system",
) -> bool:
    """Create or update the magic word in the database"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {admin_token}"}

            # First, try to find existing record
            response = await client.get(
                f"{POCKETBASE_URL}/api/collections/system_settings/records",
                params={"filter": 'key="registration_magic_word"'},
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("items") and len(data["items"]) > 0:
                    # Update existing record
                    record_id = data["items"][0]["id"]
                    update_response = await client.patch(
                        f"{POCKETBASE_URL}/api/collections/system_settings/records/{record_id}",
                        json={
                            "value": new_word,
                            "description": "Magic word required for user registration",
                            "last_updated_by": admin_email,
                        },
                        headers=headers,
                    )
                    success = update_response.status_code == 200
                else:
                    # Create new record
                    create_response = await client.post(
                        f"{POCKETBASE_URL}/api/collections/system_settings/records",
                        json={
                            "key": "registration_magic_word",
                            "value": new_word,
                            "description": "Magic word required for user registration",
                            "last_updated_by": admin_email,
                        },
                        headers=headers,
                    )
                    success = create_response.status_code == 200

                if success:
                    # Delete the old cache entry first
                    redis_client.delete("magic_word:current")
                    # Immediately set the new value in cache
                    redis_client.setex("magic_word:current", 300, new_word)

                return success
    except Exception as e:
        print(f"Error updating magic word in database: {e}")

    return False
