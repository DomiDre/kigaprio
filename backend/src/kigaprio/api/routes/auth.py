import base64
import json
import secrets
from datetime import datetime

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from kigaprio.middleware.metrics import (
    track_login_attempt,
    track_magic_word_verification,
    track_user_registration,
    update_active_sessions,
    update_admin_sessions,
)
from kigaprio.models.auth import (
    DatabaseLoginResponse,
    LoginRequest,
    LoginResponse,
    MagicWordRequest,
    MagicWordResponse,
    RegisterRequest,
    SecurityMode,
    SessionInfo,
)
from kigaprio.models.cookie import (
    COOKIE_AUTH_TOKEN,
    COOKIE_DEK,
    COOKIE_DOMAIN,
    COOKIE_PATH,
    COOKIE_SECURE,
)
from kigaprio.services.encryption import EncryptionManager
from kigaprio.services.magic_word import (
    SERVICE_ACCOUNT_ID,
    SERVICE_ACCOUNT_PASSWORD,
    get_magic_word_from_cache_or_db,
)
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import get_redis
from kigaprio.utils import (
    extract_session_info_from_record,
    get_client_ip,
    get_current_token,
    verify_token,
)

router = APIRouter()

# ============================================================================
# COOKIE CONFIGURATION
# ============================================================================


# Security mode type
def set_auth_cookies(
    response: Response,
    token: str,
    dek: bytes,
    max_age: int,
) -> None:
    """
    Set both auth_token and DEK as httpOnly cookies.

    Args:
        response: FastAPI Response object
        token: Authentication token
        dek: Data Encryption Key (raw bytes)
        max_age: Cookie lifetime in seconds
    """
    # Set auth token cookie
    response.set_cookie(
        key=COOKIE_AUTH_TOKEN,
        value=token,
        max_age=max_age,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,  # Only send over HTTPS
        httponly=True,  # Prevent JavaScript access (XSS protection)
        samesite="strict",  # CSRF protection
    )

    # Set DEK cookie
    response.set_cookie(
        key=COOKIE_DEK,
        value=base64.b64encode(dek).decode("utf-8"),
        max_age=max_age,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,
        httponly=True,  # XSS protection for encryption key!
        samesite="strict",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear both auth_token and DEK cookies."""
    response.delete_cookie(
        key=COOKIE_AUTH_TOKEN,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        key=COOKIE_DEK,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )


# ============================================================================
# PUBLIC ENDPOINTS (No Authentication Required)
# ============================================================================


@router.post("/verify-magic-word")
async def verify_magic_word(
    request: MagicWordRequest,
    req: Request,
    redis_client: redis.Redis = Depends(get_redis),
) -> MagicWordResponse:
    """Verify the magic word and return a temporary registration token."""
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

    # Check magic word (case-insensitive comparison)
    is_valid = request.magic_word.strip().lower() != magic_word.lower()
    track_magic_word_verification(is_valid)

    if not is_valid:
        # Increment rate limit counter
        redis_client.incr(rate_limit_key)
        redis_client.expire(rate_limit_key, 3600)
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
    """Register a new user with magic word token verification."""
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
            auth_response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
                json={
                    "identity": SERVICE_ACCOUNT_ID,
                    "password": SERVICE_ACCOUNT_PASSWORD,
                },
            )

            if auth_response.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Service authentication failed"
                )

            service_token = auth_response.json()["token"]

            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/records",
                headers={"Authorization": f"Bearer {service_token}"},
                json={
                    "username": request.identity,
                    "password": request.password,
                    "passwordConfirm": request.passwordConfirm,
                    "role": "user",
                    "salt": encryption_data["salt"],
                    "user_wrapped_dek": encryption_data["user_wrapped_dek"],
                    "admin_wrapped_dek": encryption_data["admin_wrapped_dek"],
                    "encrypted_fields": encrypted_fields,
                },
            )

            registration_success = response.status_code == 200
            track_user_registration(success=registration_success)
            if not registration_success:
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

            user_data = response.json()
            return {
                "success": True,
                "message": "Registrierung erfolgreich",
                "username": user_data.get("username"),
            }
    finally:
        # Remove email lock
        redis_client.delete(identity_key)


@router.post("/login")
async def login_user(
    request: LoginRequest,
    response: Response,
    req: Request,
    redis_client: redis.Redis = Depends(get_redis),
) -> LoginResponse:
    """
    Login via pocketbase, fetch session token and DEK and store
    as httpOnly cookie

    Security modes:
    - session: Logs out when browser closes (8-hour max)
    - persistent: Stays logged in (30-day max)
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

    # Rate limiting by identity
    identity_rate_limit_key = f"rate_limit:login:identity:{request.identity}"
    identity_attempts = redis_client.get(identity_rate_limit_key)

    if identity_attempts and int(str(identity_attempts)) >= 5:
        raise HTTPException(
            status_code=429,
            detail="Zu viele Login-Versuche für diesen Benutzer. Bitte versuchen Sie es in 1 Minute erneut.",
        )

    # Increment rate limit counters
    redis_client.incr(rate_limit_key)
    redis_client.expire(rate_limit_key, 60)

    redis_client.incr(identity_rate_limit_key)
    redis_client.expire(identity_rate_limit_key, 60)

    try:
        async with httpx.AsyncClient() as client:
            # Authenticate with PocketBase
            pb_response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
                json={
                    "identity": request.identity,
                    "password": request.password,
                },
            )

            if pb_response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail="Ungültige Anmeldedaten",
                )

            auth_data = DatabaseLoginResponse(**pb_response.json())

            if auth_data.record.role == "service":
                raise HTTPException(
                    status_code=403, detail="Login als Service Account verboten"
                )

            track_login_attempt("success", client_ip)

            # Reset rate limits on successful login
            redis_client.delete(rate_limit_key)
            redis_client.delete(identity_rate_limit_key)

            # Extract user information
            user_record = auth_data.record
            token = auth_data.token

            # Determine security mode (from request or user's stored preference)
            security_mode: SecurityMode = (
                "persistent" if request.keep_logged_in else "session"
            )

            # Unwrap user's DEK using their password
            dek = EncryptionManager.get_user_dek(
                request.password,
                user_record.salt,
                user_record.user_wrapped_dek,
            )

            # Store session info in Redis
            session_key = f"session:{token}"
            session_info = extract_session_info_from_record(user_record)
            is_admin: bool = session_info.is_admin

            # Determine session/cookie duration based on mode
            if security_mode == "session":
                session_ttl = 8 * 3600  # 8 hours
                cookie_max_age = 8 * 3600
            else:  # persistent
                session_ttl = 30 * 24 * 3600  # 30 days
                cookie_max_age = 30 * 24 * 3600

            # Admin sessions always have shorter TTL
            if is_admin:
                session_ttl = 900  # 15 minutes
                cookie_max_age = 900

            # Store session metadata in Redis
            redis_client.setex(
                session_key,
                session_ttl,
                session_info.model_dump_json(),
            )

            if is_admin:
                # Count active admin sessions
                admin_count = redis_client.scard("active_admin_sessions") or 0
                update_admin_sessions(int(admin_count))
            else:
                # Count user sessions by mode
                mode_key = f"active_{security_mode}_sessions"
                mode_count = redis_client.scard(mode_key) or 0
                update_active_sessions(int(mode_count), security_mode)

            # set auth_token and dek as httponly cookies
            set_auth_cookies(response, token, dek, cookie_max_age)

            return LoginResponse(
                message="Erfolgreich als Administrator angemeldet"
                if is_admin
                else "Erfolgreich angemeldet",
            )

    except HTTPException:
        raise
    except Exception as e:
        track_login_attempt("error", client_ip)
        raise HTTPException(
            status_code=500,
            detail="Ein unerwarteter Fehler ist aufgetreten",
        ) from e


# ============================================================================
# PROTECTED ENDPOINTS (Authentication Required)
# ============================================================================


@router.post("/logout")
async def logout_user(
    response: Response,
    token: str = Depends(get_current_token),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Logout a user by invalidating their session and clearing cookies."""
    session_key = f"session:{token}"

    # Delete session from Redis
    redis_client.delete(session_key)

    # Clear both httpOnly cookies
    clear_auth_cookies(response)

    return {"success": True, "message": "Erfolgreich abgemeldet"}


@router.get("/verify")
async def verify_session(
    current_session: SessionInfo = Depends(verify_token),
):
    """
    Verify that the current session is valid.

    Used by the client on page load to check if they have a valid session.
    Returns basic user info if authenticated.
    """

    return {
        "authenticated": True,
        "user_id": current_session.id,
        "username": current_session.username,
        "is_admin": current_session.is_admin,
    }


@router.post("/change-password")
async def change_password(
    current_session: SessionInfo = Depends(verify_token),
):
    """
    Change user password.

    TODO: Implement password change logic:
    1. Verify current password
    2. Unwrap DEK with old password
    3. Rewrap DEK with new password
    4. Update database
    5. Invalidate all existing sessions
    """
    # TODO: Implement this
    _ = current_session
    return {"message": "Not implemented yet"}
