import json
import os
import secrets
from datetime import datetime

import httpx
import redis
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from kigaprio.services.magic_word import (
    get_magic_word_from_cache_or_db,
)
from kigaprio.services.redis_service import (
    cache_admin_identity,
    get_redis,
    remove_admin_identity,
)
from kigaprio.utils import check_if_likely_admin, get_client_ip

router = APIRouter()
security = HTTPBearer()

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


class LoginRequest(BaseModel):
    identity: str = Field(..., min_length=1, description="Email or username")
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    record: dict
    message: str | None = None


async def _try_admin_auth(
    client: httpx.AsyncClient, identity: str, password: str
) -> dict | None:
    """
    Attempt admin authentication against PocketBase.
    Returns auth data if successful, None otherwise.
    """
    try:
        response = await client.post(
            f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
            json={
                "identity": identity,
                "password": password,
            },
        )

        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


async def get_current_user(
    authorization: str = Header(None),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Extract user info from token, including admin status"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")
    session_key = f"session:{token}"

    user_data = redis_client.get(session_key)
    if not user_data:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return json.loads(str(user_data))


async def require_admin(current_user: dict = Depends(get_current_user)):
    """Ensure the current user is an admin"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def _try_user_auth(
    client: httpx.AsyncClient, identity: str, password: str
) -> dict | None:
    """
    Attempt regular user authentication against PocketBase.
    Returns auth data if successful, None otherwise.
    """
    try:
        response = await client.post(
            f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
            json={
                "identity": identity,
                "password": password,
            },
        )

        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


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
                    "email": request.email.lower(),
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


@router.post("/login")
async def login_user(
    request: LoginRequest,
    req: Request,
    redis_client: redis.Redis = Depends(get_redis),
) -> LoginResponse:
    """Authenticate a user and return auth token from PocketBase.

    This endpoint intelligently determines whether the user is likely an admin
    and authenticates against the appropriate collection.
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
    identity_rate_limit_key = f"rate_limit:login:identity:{request.identity.lower()}"
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

    # Determine if this might be an admin login
    is_likely_admin = check_if_likely_admin(request.identity.lower(), redis_client)

    try:
        async with httpx.AsyncClient() as client:
            auth_data = None
            is_admin = False

            if is_likely_admin:
                # Try admin authentication first
                auth_data = await _try_admin_auth(
                    client, request.identity.lower(), request.password
                )
                if auth_data:
                    is_admin = True
                    # Cache this identity as admin for future logins
                    cache_admin_identity(request.identity.lower(), redis_client)
                else:
                    # Admin auth failed, try regular user
                    auth_data = await _try_user_auth(
                        client, request.identity.lower(), request.password
                    )
                    if auth_data:
                        # This identity is not an admin, remove from cache if present
                        remove_admin_identity(request.identity.lower(), redis_client)
            else:
                # Try regular user authentication first
                auth_data = await _try_user_auth(
                    client, request.identity.lower(), request.password
                )
                if not auth_data:
                    # User auth failed, try admin as fallback
                    auth_data = await _try_admin_auth(
                        client, request.identity.lower(), request.password
                    )
                    if auth_data:
                        is_admin = True
                        # Cache this identity as admin for future logins
                        cache_admin_identity(request.identity.lower(), redis_client)

            if not auth_data:
                # Both authentication attempts failed
                raise HTTPException(
                    status_code=401,
                    detail="Ungültige Anmeldedaten",
                )

            # Reset rate limits on successful login
            redis_client.delete(rate_limit_key)
            redis_client.delete(identity_rate_limit_key)

            # Store session
            session_key = f"session:{auth_data['token']}"
            session_info = {
                "id": auth_data["record"]["id"],
                "email": auth_data["record"]["email"],
                "name": auth_data["record"].get(
                    "name", "Admin" if is_admin else "User"
                ),
                "is_admin": is_admin,
                "type": "superuser" if is_admin else "user",
            }

            # Different TTL for admin vs regular users
            ttl = (
                900 if is_admin else (14 * 24 * 3600)
            )  # 15 min for admin, 14 days for users
            redis_client.setex(
                session_key,
                ttl,
                json.dumps(session_info),
            )

            return LoginResponse(
                token=auth_data["token"],
                record={**auth_data["record"], "is_admin": is_admin},
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


@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Refresh an authentication token.

    This endpoint proxies to PocketBase's auth-refresh endpoint.
    """

    token = credentials.credentials
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-refresh",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get(
                        "message", "Token-Aktualisierung fehlgeschlagen"
                    ),
                )

            # Parse successful response
            auth_data = response.json()

            # Update session in Redis with new token
            old_session_key = f"session:{token}"
            new_session_key = f"session:{auth_data['token']}"

            # Copy session data to new key if it exists
            session_data = redis_client.get(old_session_key)
            user_info = {
                "id": auth_data["record"]["id"],
                "email": auth_data["record"]["email"],
                "name": auth_data["record"]["name"],
            }
            if session_data:
                redis_client.delete(old_session_key)

            redis_client.setex(
                new_session_key,
                14 * 24 * 3600,  # 14 days
                json.dumps(user_info),
            )
            return {
                "token": auth_data["token"],
                "record": auth_data["record"],
                "message": "Token erfolgreich aktualisiert",
            }

    except HTTPException:
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

    Note: This only removes the session from Redis cache.
    The PocketBase token will still be valid until it expires.
    For complete logout, the client should also delete the token.
    """
    token = credentials.credentials
    session_key = f"session:{token}"

    # Check if session exists
    if not redis_client.exists(session_key):
        raise HTTPException(
            status_code=404,
            detail="Sitzung nicht gefunden oder bereits abgelaufen",
        )

    # Delete session from Redis
    redis_client.delete(session_key)

    return {"success": True, "message": "Erfolgreich abgemeldet"}
