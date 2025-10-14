import base64
import json
import secrets
from datetime import datetime
from typing import Any, Literal

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kigaprio.models.auth import (
    DatabaseLoginResponse,
    LoginRequest,
    LoginResponse,
    MagicWordRequest,
    MagicWordResponse,
    RegisterRequest,
)
from kigaprio.services.encryption import EncryptionManager
from kigaprio.services.magic_word import (
    get_magic_word_from_cache_or_db,
)
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import (
    get_redis,
)
from kigaprio.utils import extract_session_info_from_record, get_client_ip

router = APIRouter()
security = HTTPBearer()


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
        raise HTTPException(status_code=500, detail="No magic word is initialized")

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
    identity_key = f"reg_identity:{request.identity}"
    if redis_client.exists(identity_key):
        raise HTTPException(
            status_code=429,
            detail="Eine Registrierung für diese E-Mail-Adresse läuft bereits",
        )

    # Set temporary lock on email (5 minutes)
    redis_client.setex(identity_key, 300, "registering")

    try:
        # Create data encryption key
        encryption_data = EncryptionManager.create_user_encryption_data(
            request.password
        )
        dek = EncryptionManager.get_user_dek(
            request.password,
            encryption_data["salt"],
            encryption_data["user_wrapped_dek"],
        )

        # encrypt sensitive data
        encrypted_fields = EncryptionManager.encrypt_fields({"name": request.name}, dek)

        # Proxy registration to PocketBase
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/records",
                json={
                    "username": request.identity,
                    "password": request.password,
                    "passwordConfirm": request.passwordConfirm,
                    "role": "user",
                    "salt": encryption_data["salt"],
                    "user_wrapped_dek": encryption_data["user_wrapped_dek"],
                    "admin_wrapped_dek": encryption_data["admin_wrapped_dek"],
                    "encrypted_fields": encrypted_fields,
                    "security_tier": request.security_tier,
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
        redis_client.delete(identity_key)


@router.post("/login")
async def login_user(
    request: LoginRequest,
    req: Request,
    redis_client: redis.Redis = Depends(get_redis),
) -> LoginResponse:
    """Authenticate a user and return auth token with DEK based on security tier.

    Security tier handling:
    - High: DEK returned directly to client (sessionStorage only)
    - Balanced: DEK split into server part (Redis cache) and client part (sessionStorage)
    - Convenience: DEK returned directly to client (localStorage)
    """

    # Rate limiting by IP
    client_ip = get_client_ip(req)
    rate_limit_key = f"rate_limit:login:{client_ip}"
    attempts = redis_client.get(rate_limit_key)

    if attempts and int(str(attempts)) >= 5:
        raise HTTPException(
            status_code=429,
            detail="Zu viele Login-Versuche. Bitte versuchen Sie es in 1 Minute erneut.",
        )

    # Rate limiting by identity (email/username)
    identity_rate_limit_key = f"rate_limit:login:identity:{request.identity}"
    identity_attempts = redis_client.get(identity_rate_limit_key)

    if identity_attempts and int(str(identity_attempts)) >= 5:
        raise HTTPException(
            status_code=429,
            detail="Zu viele Login-Versuche für diesen Benutzer. Bitte versuchen Sie es in 1 Minute erneut.",
        )

    # Increment rate limit counters
    redis_client.incr(rate_limit_key)
    redis_client.expire(rate_limit_key, 60)  # 1 min expiry

    redis_client.incr(identity_rate_limit_key)
    redis_client.expire(identity_rate_limit_key, 60)  # 1 min expiry

    try:
        async with httpx.AsyncClient() as client:
            # Authenticate with PocketBase
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
                json={
                    "identity": request.identity,
                    "password": request.password,
                },
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail="Ungültige Anmeldedaten",
                )

            auth_data = DatabaseLoginResponse(**response.json())

            if auth_data.record.role == "service":
                raise HTTPException(
                    status_code=403, detail="Login als Service Account verboten"
                )

            # Reset rate limits on successful login
            redis_client.delete(rate_limit_key)
            redis_client.delete(identity_rate_limit_key)

            # Extract user information
            user_record = auth_data.record
            token = auth_data.token

            # Determine security tier (from request or user's stored preference)
            security_tier: Literal["high", "balanced", "convenience"] = (
                request.security_tier
                if hasattr(request, "security_tier") and request.security_tier
                else user_record.security_tier
            )

            # Unwrap user's DEK using their password
            dek = EncryptionManager.get_user_dek(
                request.password,
                user_record.salt,
                user_record.user_wrapped_dek,
            )

            # Store session info
            session_key = f"session:{token}"
            session_info = extract_session_info_from_record(user_record)
            is_admin: bool = session_info.is_admin

            # Handle DEK based on security tier
            dek_data: dict[str, Any] = {}

            match security_tier:
                case "balanced":
                    # Split-key system: divide DEK into server and client parts
                    server_part, client_part = EncryptionManager.split_dek(dek)

                    # Encrypt server part before caching
                    encrypted_server_part = EncryptionManager.encrypt_dek_part(
                        server_part
                    )
                    print(encrypted_server_part)

                    # Store encrypted server part in Redis with 30-minute TTL
                    dek_cache_key = f"dek:{user_record.id}:{token}"
                    dek_cache_data = {
                        "encrypted_server_part": encrypted_server_part,
                        "created_at": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat(),
                    }
                    redis_client.setex(
                        dek_cache_key,
                        1800,  # 30 minutes
                        json.dumps(dek_cache_data),
                    )

                    dek_data = {
                        "client_key_part": client_part,
                    }

                    # Session TTL: 8 hours max for balanced mode
                    session_ttl = 8 * 3600

                case "high":
                    # High security: full DEK to client, nothing cached on server
                    dek_data = {
                        "dek": base64.b64encode(dek).decode("utf-8"),
                    }

                    # Session TTL: tab lifetime (client manages this)
                    session_ttl = 8 * 3600  # Max duration for session record, 8h

                case "convenience":
                    # Convenience: full DEK to client, persistent storage
                    dek_data = {
                        "dek": base64.b64encode(dek).decode("utf-8"),
                    }

                    # Session TTL: until explicit logout
                    session_ttl = 30 * 24 * 3600  # 30 days

            # Admin sessions always have shorter TTL
            if is_admin:
                session_ttl = 900  # 15 minutes for admins

            # Store session metadata
            redis_client.setex(
                session_key,
                session_ttl,
                session_info.model_dump_json(),
            )

            return LoginResponse(
                token=token,
                security_tier=security_tier,
                **dek_data,
                message="Erfolgreich als Administrator angemeldet"
                if is_admin
                else "Erfolgreich angemeldet",
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Ein unerwarteter Fehler ist aufgetreten",
        ) from e


@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Logout a user by invalidating their session.

    For balanced security mode, also removes cached DEK parts.
    Note: The PocketBase token will still be valid until it expires.
    For complete logout, the client should also delete the token and DEK.
    """
    token = credentials.credentials
    session_key = f"session:{token}"

    # Check if session exists
    session_data = redis_client.get(session_key)
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail="Sitzung nicht gefunden oder bereits abgelaufen",
        )

    # Extract user ID from session to clean up DEK cache
    try:
        session_info = json.loads(str(session_data))
        user_id = session_info.get("id")

        # Remove DEK cache for balanced mode
        if user_id:
            dek_cache_key = f"dek:{user_id}:{token}"
            redis_client.delete(dek_cache_key)
    except (json.JSONDecodeError, KeyError):
        pass  # Continue with logout even if cleanup fails

    # Delete session from Redis
    redis_client.delete(session_key)

    return {"success": True, "message": "Erfolgreich abgemeldet"}


@router.post("/change-password")
async def change_password(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    return {"message": "Not implemented yet"}
