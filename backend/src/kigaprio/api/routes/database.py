import json
import os
import secrets
from datetime import datetime

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from kigaprio.services.magic_word import (
    DEFAULT_MAGIC_WORD,
    get_magic_word_from_cache_or_db,
)
from kigaprio.services.redis_service import get_redis

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
    password: str = Field(..., min_length=8)
    passwordConfirm: str
    name: str = Field(..., min_length=1)
    registration_token: str


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check for X-Forwarded-For header (when behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection
    return request.client.host if request.client else "127.0.0.1"


def log_registration_attempt(
    redis_client: redis.Redis, success: bool, email: str | None = None
):
    """Log registration attempts for monitoring"""
    date_key = f"stats:registrations:{datetime.now().strftime('%Y%m%d')}"

    if success:
        redis_client.hincrby(date_key, "successful", 1)
        # Log successful registration emails (hashed for privacy)
        if email:
            import hashlib

            email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:8]
            redis_client.sadd(
                f"stats:registered_users:{datetime.now().strftime('%Y%m%d')}",
                email_hash,
            )
    else:
        redis_client.hincrby(date_key, "failed", 1)
        # Track failed attempts per email domain
        if email and "@" in email:
            domain = email.split("@")[1]
            redis_client.hincrby(
                f"stats:failed_domains:{datetime.now().strftime('%Y%m%d')}", domain, 1
            )

    # Expire after 90 days
    redis_client.expire(date_key, 7776000)


@router.post("/verify-magic-word")
async def verify_magic_word(
    request: MagicWordRequest,
    req: Request,
    redis_client: redis.Redis = Depends(get_redis),
) -> MagicWordResponse:
    """Verify the magic word and return a temporary registration token"""

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
        # Log failed attempt
        redis_client.hincrby(
            f"stats:magic_word_failures:{datetime.now().strftime('%Y%m%d')}",
            client_ip,
            1,
        )
        raise HTTPException(status_code=403, detail="Ungültiges Zauberwort")

    # Reset rate limit on success
    redis_client.delete(rate_limit_key)

    # Generate temporary token
    token = secrets.token_urlsafe(32)

    # Store token in Redis with 10 minute expiration
    token_key = f"reg_token:{token}"
    token_data = {"created_at": datetime.now().isoformat(), "ip": client_ip}
    redis_client.setex(token_key, 600, json.dumps(token_data))

    # Log successful verification
    redis_client.hincrby(
        f"stats:magic_word_success:{datetime.now().strftime('%Y%m%d')}", "count", 1
    )

    return MagicWordResponse(
        success=True, token=token, message="Zauberwort erfolgreich verifiziert"
    )


@router.post("/register")
async def register_user(
    request: RegisterRequest, redis_client: redis.Redis = Depends(get_redis)
):
    """Register a new user with magic word token verification"""

    # Verify registration token
    token_key = f"reg_token:{request.registration_token}"
    token_data = redis_client.get(token_key)

    if not token_data:
        log_registration_attempt(redis_client, False)
        raise HTTPException(
            status_code=403, detail="Ungültiger oder abgelaufener Registrierungstoken"
        )

    # Delete token (one-time use)
    redis_client.delete(token_key)

    # Check for duplicate registration attempts
    email_key = f"reg_email:{request.email.lower()}"
    if redis_client.exists(email_key):
        log_registration_attempt(redis_client, False, request.email)
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
                log_registration_attempt(redis_client, False, request.email)
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

            # Log successful registration
            log_registration_attempt(redis_client, True, request.email)

            # Store registration metadata
            user_data = response.json()
            redis_client.setex(
                f"user:registered:{user_data['id']}",
                86400,  # 24 hours
                json.dumps(
                    {
                        "email": request.email,
                        "name": request.name,
                        "registered_at": datetime.now().isoformat(),
                    }
                ),
            )

            return user_data

    finally:
        # Remove email lock
        redis_client.delete(email_key)


# ==================== Proxy Endpoints ====================
async def proxy_to_pocketbase(path: str, request: Request) -> Response:
    """Shared proxy logic for PocketBase"""
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"{POCKETBASE_URL}/{path}",
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=await request.body(),
            params=request.query_params,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )


@router.get("/pb/{path:path}")
async def proxy_get(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)


@router.post("/pb/{path:path}")
async def proxy_post(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)


@router.put("/pb/{path:path}")
async def proxy_put(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)


@router.delete("/pb/{path:path}")
async def proxy_delete(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)


@router.patch("/pb/{path:path}")
async def proxy_patch(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)
