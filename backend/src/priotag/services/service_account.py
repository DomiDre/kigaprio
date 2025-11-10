"""Service account authentication utilities"""

import logging
from pathlib import Path

import httpx

from priotag.services.pocketbase_service import POCKETBASE_URL

logger = logging.getLogger(__name__)

# Service account credentials from secrets
service_id_file = Path("/run/secrets/pb_service_id")
service_password_file = Path("/run/secrets/pb_service_password")

if not service_id_file.exists() or not service_password_file.exists():
    logger.warning("Service ID/password are not set on backend as secret")

SERVICE_ACCOUNT_ID = (
    service_id_file.read_text().strip() if service_id_file.exists() else "pb_service"
)
SERVICE_ACCOUNT_PASSWORD = (
    service_password_file.read_text().strip()
    if service_password_file.exists()
    else "password"
)


async def authenticate_service_account(client: httpx.AsyncClient) -> str | None:
    """
    Authenticate as service account to PocketBase and return the auth token.

    Args:
        client: An httpx.AsyncClient instance to use for the request

    Returns:
        Auth token if successful, None otherwise

    Example:
        ```python
        async with httpx.AsyncClient() as client:
            token = await authenticate_service_account(client)
            if token:
                headers = {"Authorization": f"Bearer {token}"}
                # Use headers for authenticated requests
        ```
    """
    try:
        response = await client.post(
            f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
            json={
                "identity": SERVICE_ACCOUNT_ID,
                "password": SERVICE_ACCOUNT_PASSWORD,
            },
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            logger.debug("Service account authenticated successfully")
            return token
        else:
            logger.error(
                f"Service account authentication failed: "
                f"{response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        logger.error(f"Error during service account authentication: {e}")
        return None
