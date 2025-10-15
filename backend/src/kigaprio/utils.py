import json
from typing import Annotated

import httpx
import redis
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kigaprio.models.auth import DEKData, SessionInfo, TokenVerificationData
from kigaprio.models.pocketbase_schemas import UsersResponse
from kigaprio.services.encryption import EncryptionManager
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import get_redis

security = HTTPBearer()


async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(get_redis),
) -> TokenVerificationData:
    """Verify the authentication token - first check Redis, then PocketBase if needed."""
    token = credentials.credentials
    session_key = f"session:{token}"
    cached_user = redis_client.get(session_key)

    if cached_user:
        # Token found in cache - it's valid
        return TokenVerificationData(
            token=token, user=SessionInfo(**json.loads(str(cached_user)))
        )

    # Token not in cache - verify with PocketBase
    async with httpx.AsyncClient() as client:
        # IMPORTANT: This will refresh the token and return a NEW one
        response = await client.post(  # Note: POST, not GET
            f"{POCKETBASE_URL}/api/collections/users/auth-refresh",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Ungültiger oder abgelaufener Token",
            )

        auth_data = response.json()
        new_token = auth_data["token"]
        user_data = UsersResponse(**auth_data["record"])

        # Delete old session and create new one with refreshed token
        redis_client.delete(session_key)  # Remove old token

        new_session_key = f"session:{new_token}"
        session_info = extract_session_info_from_record(user_data)
        is_admin = session_info.is_admin
        ttl = (
            900 if is_admin else (14 * 24 * 3600)
        )  # 15 min for admin, 14 days for users

        redis_client.setex(
            new_session_key,
            ttl,
            session_info.model_dump_json(),
        )

        if new_token != token:
            request.state.new_token = new_token

        return TokenVerificationData(
            token=token,
            new_token=new_token if new_token != token else None,
            user=session_info,
        )


def extract_session_info_from_record(record: UsersResponse) -> SessionInfo:
    is_admin = record.role == "admin"
    return SessionInfo(
        id=record.id,
        username=record.username,
        security_tier=record.security_tier,
        is_admin=is_admin,
    )


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


async def get_dek_from_request(
    x_dek: Annotated[str, Header(description="DEK or client key part")],
    auth_data: TokenVerificationData = Depends(verify_token),
    redis_client: redis.Redis = Depends(get_redis),
) -> DEKData:
    """Extract and reconstruct DEK from request headers.

    Client should send either:
    - Full DEK (base64) for high/convenience modes
    - Client key part (base64) for balanced mode

    Header: X-DEK: <base64_encoded_dek_or_part>
    """
    try:
        dek = EncryptionManager.get_dek_from_request(
            dek_or_client_part=x_dek,
            user_id=auth_data.user.id,
            token=auth_data.token,
            security_tier=auth_data.user.security_tier,
            redis_client=redis_client,
        )

        return DEKData(
            dek=dek,
            user_id=auth_data.user.id,
            security_tier=auth_data.user.security_tier,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Fehler bei der Schlüsselverarbeitung",
        ) from e
