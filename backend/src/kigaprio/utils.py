import base64
import json
import logging

import httpx
import redis
from fastapi import Cookie, Depends, HTTPException, Request, Response

from kigaprio.models.auth import SessionInfo
from kigaprio.models.cookie import (
    COOKIE_AUTH_TOKEN,
    COOKIE_DEK,
    COOKIE_PATH,
    COOKIE_SECURE,
)
from kigaprio.models.pocketbase_schemas import UsersResponse
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import get_redis

# Cookie names


async def get_current_token(
    auth_token: str | None = Cookie(None, alias=COOKIE_AUTH_TOKEN),
) -> str:
    """Extract auth token from httpOnly cookie."""
    if not auth_token:
        raise HTTPException(
            status_code=401,
            detail="Nicht authentifiziert - keine gültige Sitzung gefunden",
        )
    return auth_token


async def get_current_dek(
    dek: str | None = Cookie(None, alias=COOKIE_DEK),
) -> bytes:
    """Extract DEK from httpOnly cookie."""
    if not dek:
        raise HTTPException(
            status_code=400,
            detail="Verschlüsselungsschlüssel nicht gefunden",
        )
    try:
        return base64.b64decode(dek)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Ungültiger Verschlüsselungsschlüssel",
        ) from e


async def verify_token(
    response: Response,
    token: str = Depends(get_current_token),
    redis_client: redis.Redis = Depends(get_redis),
) -> SessionInfo:
    """
    Verify authentication token from cookie.

    First checks Redis cache, then validates with PocketBase if needed.
    If PocketBase returns a new token, updates the cookie.
    """
    logger = logging.getLogger(__name__)

    session_key = f"session:{token}"

    try:
        cached_session = redis_client.get(session_key)
        logger.debug(
            f"Redis lookup for {session_key}: {'found' if cached_session else 'not found'}"
        )
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        # If Redis fails, try PocketBase refresh
        cached_session = None

    if cached_session:
        # Session found in cache - it's valid
        try:
            session_data = (
                json.loads(cached_session)
                if isinstance(cached_session, str)
                else json.loads(str(cached_session))
            )
            return SessionInfo(**session_data)
        except Exception as e:
            logger.error(f"Failed to parse cached session: {e}")
            # If parsing fails, fall through to PocketBase refresh

    # Session not in cache - verify with PocketBase
    logger.debug(
        f"Session not in cache, refreshing with PocketBase for token: {token[:10]}..."
    )

    async with httpx.AsyncClient() as client:
        try:
            pb_response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-refresh",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,  # Add timeout
            )

            if pb_response.status_code != 200:
                logger.warning(
                    f"PocketBase auth refresh failed: {pb_response.status_code}"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Ungültiger oder abgelaufener Token",
                )

            auth_data = pb_response.json()
            new_token = auth_data["token"]
            user_data = UsersResponse(**auth_data["record"])

            # Extract session info
            session_info = extract_session_info_from_record(user_data)
            is_admin = session_info.is_admin

            # Determine TTL and cookie max_age
            if is_admin:
                ttl = 900  # 15 minutes
                cookie_max_age = 900
            else:
                # Default to "session" mode when restoring (safer)
                ttl = 8 * 3600  # 8 hours
                cookie_max_age = 8 * 3600

            # If token was refreshed, update cookie and Redis with new token
            if new_token != token:
                logger.info("Token refreshed, updating Redis and cookies")
                # Delete old session
                try:
                    redis_client.delete(session_key)
                except Exception as e:
                    logger.warning(f"Failed to delete old session from Redis: {e}")

                # Store new session with new token
                new_session_key = f"session:{new_token}"
                try:
                    redis_client.setex(
                        new_session_key,
                        ttl,
                        session_info.model_dump_json(),
                    )
                except Exception as e:
                    logger.error(f"Failed to store new session in Redis: {e}")
                    # Continue anyway - PocketBase token is valid

                # Update cookie with new token
                response.set_cookie(
                    key=COOKIE_AUTH_TOKEN,
                    value=new_token,
                    max_age=cookie_max_age,
                    httponly=True,
                    secure=COOKIE_SECURE,
                    samesite="strict",
                    path=COOKIE_PATH,
                )
            else:
                # Same token, just restore to Redis
                logger.debug("Restoring session to Redis cache")
                try:
                    redis_client.setex(
                        session_key,
                        ttl,
                        session_info.model_dump_json(),
                    )
                except Exception as e:
                    logger.error(f"Failed to restore session to Redis: {e}")
                    # Continue anyway - PocketBase token is valid

            return session_info

        except httpx.RequestError as e:
            logger.error(f"PocketBase connection error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Authentifizierungsserver nicht erreichbar",
            ) from e


async def require_admin(
    session: SessionInfo = Depends(verify_token),
) -> SessionInfo:
    """Dependency that requires admin role."""
    if not session.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Administratorrechte erforderlich",
        )
    return session


def extract_session_info_from_record(record: UsersResponse) -> SessionInfo:
    """Extract session info from PocketBase user record."""
    is_admin = record.role == "admin"
    return SessionInfo(
        id=record.id,
        username=record.username,
        is_admin=is_admin,
    )


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
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
