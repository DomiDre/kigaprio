import json
import os
import secrets
from datetime import datetime

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from kigaprio.services.magic_word import (
    DEFAULT_MAGIC_WORD,
    get_magic_word_from_cache_or_db,
)
from kigaprio.services.redis_service import get_redis
from kigaprio.utils import get_client_ip

router = APIRouter()

# Configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")


class MagicWordRequest(BaseModel):
    magic_word: str = Field(..., min_length=1)


class MagicWordResponse(BaseModel):
    success: bool
    token: str | None = None
    message: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    passwordConfirm: str
    name: str = Field(..., min_length=1)
    registration_token: str


@router.post("/verify-magic-word")
async def verify_magic_word(
    request: MagicWordRequest,
    req: Request,
    redis_client: redis.Redis = Depends(get_redis),
) -> MagicWordResponse:
    """Verify the magic word and return a temporary registration token.
    This endpoint is triggered before a registration and therefore anybody
    should be able to call it.

    However to avoid spam, rate limits are implemented.
    """

    # determine if there are too many requests by client_ip
    client_ip = get_client_ip(req)
    rate_limit_key = f"rate_limit:magic_word:{client_ip}"
    attempts = redis_client.get(rate_limit_key)

    if attempts and int(str(attempts)) >= 10:
        raise HTTPException(
            status_code=429,
            detail="Zu viele Versuche. Bitte versuchen Sie es später erneut.",
        )

    # Get magic word from cache/database
    magic_word = await get_magic_word_from_cache_or_db(redis_client)
    if not magic_word:
        magic_word = DEFAULT_MAGIC_WORD

    # Increment rate limit counter
    redis_client.incr(rate_limit_key)
    redis_client.expire(rate_limit_key, 3600)

    # Check magic word (case-insensitive comparison)
    if request.magic_word.strip().lower() != magic_word.lower():
        raise HTTPException(status_code=403, detail="Ungültiges Zauberwort")

    # Reset rate limit on success
    redis_client.delete(rate_limit_key)

    # Generate temporary token
    token = secrets.token_urlsafe(32)

    # Store token in Redis with 10 minute expiration
    token_key = f"reg_token:{token}"
    token_data = {"created_at": datetime.now().isoformat(), "ip": client_ip}
    redis_client.setex(token_key, 600, json.dumps(token_data))

    return MagicWordResponse(
        success=True, token=token, message="Zauberwort erfolgreich verifiziert"
    )


@router.post("/register")
async def register_user(
    request: RegisterRequest, redis_client: redis.Redis = Depends(get_redis)
):
    """Register a new user with magic word token verification.

    As only people who have passed magic word check may register. This
    endpoint can still be called by anyone, but the token check must
    be passed at the beginning.
    """

    # Verify registration token
    token_key = f"reg_token:{request.registration_token}"
    token_data = redis_client.get(token_key)

    if not token_data:
        raise HTTPException(
            status_code=403, detail="Ungültiger oder abgelaufener Registrierungstoken"
        )

    # Delete token (one-time use)
    redis_client.delete(token_key)

    # Check for duplicate registration attempts
    email_key = f"reg_email:{request.email.lower()}"
    if redis_client.exists(email_key):
        raise HTTPException(
            status_code=429,
            detail="Eine Registrierung für diese E-Mail-Adresse läuft bereits",
        )

    # Set temporary lock on email (5 minutes)
    redis_client.setex(email_key, 300, "registering")

    try:
        # Proxy registration to PocketBase
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/records",
                json={
                    "email": request.email,
                    "password": request.password,
                    "passwordConfirm": request.passwordConfirm,
                    "name": request.name,
                    "role": "user",
                },
            )

            if response.status_code != 200:
                error_data = response.json()

                # Handle PocketBase validation errors
                if "data" in error_data:
                    errors = []
                    for field, msgs in error_data["data"].items():
                        if field == "email":
                            errors.append(
                                "Email-Adresse ist bereits registriert oder ungültig"
                            )
                        elif field == "password":
                            errors.append("Passwort entspricht nicht den Anforderungen")
                        else:
                            errors.append(f"{field}: {msgs['message']}")
                    raise HTTPException(status_code=400, detail=". ".join(errors))

                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message", "Registrierung fehlgeschlagen"),
                )

            # Store registration metadata
            user_data = response.json()
            return user_data
    finally:
        # Remove email lock
        redis_client.delete(email_key)
