import os
from pathlib import Path

import httpx
from fastapi import HTTPException, Request, UploadFile, status

from kigaprio.config import settings

POCKETBASE_URL = os.getenv("POCKETBASE_URL")
assert POCKETBASE_URL is not None, "Pocketbase URL not specified by env"


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


async def validate_token(request: Request):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    token_value = token[len("Bearer ") :]

    async with httpx.AsyncClient() as client:
        # Verify session using PocketBase API
        response = await client.get(
            f"{POCKETBASE_URL}/api/collections/users/records",
            headers={"Authorization": f"Bearer {token_value}"},
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        print(response.text)
    return token_value
