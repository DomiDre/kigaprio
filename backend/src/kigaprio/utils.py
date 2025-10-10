import json
from pathlib import Path

import httpx
import redis
from fastapi import Depends, HTTPException, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kigaprio.config import settings
from kigaprio.models.auth import SessionInfo, TokenVerificationData
from kigaprio.models.pocketbase_schemas import UsersResponse
from kigaprio.services.pocketbase_service import POCKETBASE_URL
from kigaprio.services.redis_service import get_redis

security = HTTPBearer()


async def validate_file(files: list[UploadFile]) -> list[UploadFile]:
    """Validate uploaded files."""

    for file in files:
        if file.size is None:
            raise HTTPException(status_code=400, detail="File size is zero")
        if file.filename is None:
            raise HTTPException(status_code=400, detail="Received file without name")
        # Check file size
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File {file.filename} is too large. Max size: {settings.MAX_FILE_SIZE} bytes",
            )

        # Check file extension
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"File type {file_ext} not supported. Allowed: {settings.ALLOWED_EXTENSIONS}",
            )

    return files


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
        name=record.name,
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
