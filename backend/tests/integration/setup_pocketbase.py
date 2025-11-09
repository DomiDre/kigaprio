"""
Setup script for PocketBase in CI mode.

This script initializes PocketBase with the magic word and service account.
It should be run from inside the backend container before tests.
"""

import os
import time

import httpx


def setup_pocketbase():
    """Set up PocketBase with required data (magic word and service account)."""
    pocketbase_url = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")
    superuser_login = "admin@example.com"
    superuser_password = "admintest"
    magic_word = "test"

    print(f"Setting up PocketBase at {pocketbase_url}...")

    # Wait for PocketBase to be ready
    print("Waiting for PocketBase to be ready...")
    for i in range(60):
        try:
            response = httpx.get(f"{pocketbase_url}/api/health", timeout=1.0)
            if response.status_code == 200:
                print("✓ PocketBase is ready")
                break
        except (httpx.RequestError, httpx.TimeoutException):
            if i % 10 == 0:
                print(f"  Still waiting... ({i}s)")
            time.sleep(1)
    else:
        raise RuntimeError("PocketBase did not become ready in time")

    client = httpx.Client(base_url=pocketbase_url, timeout=10.0)

    # Authenticate as admin
    print("Authenticating as admin...")
    response = client.post(
        "/api/collections/_superusers/auth-with-password",
        json={
            "identity": superuser_login,
            "password": superuser_password,
        },
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to authenticate as admin: {response.status_code} - {response.text}"
        )
    token = response.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    print("✓ Authenticated as admin")

    # Create magic word setting
    print(f"Creating magic word setting (value='{magic_word}')...")
    create_response = client.post(
        "/api/collections/system_settings/records",
        json={
            "key": "registration_magic_word",
            "value": magic_word,
            "description": "Magic word required for user registration",
            "last_updated_by": superuser_login,
        },
    )
    if create_response.status_code != 200:
        raise RuntimeError(
            f"Failed to create magic word: {create_response.status_code} - {create_response.text}"
        )
    print("✓ Magic word created")

    # Create service account
    from kigaprio.services import service_account

    print(f"Creating service account ({service_account.SERVICE_ACCOUNT_ID})...")
    service_response = client.post(
        "/api/collections/users/records",
        json={
            "username": service_account.SERVICE_ACCOUNT_ID,
            "password": service_account.SERVICE_ACCOUNT_PASSWORD,
            "passwordConfirm": service_account.SERVICE_ACCOUNT_PASSWORD,
            "role": "service",
        },
    )
    if service_response.status_code != 200:
        print(
            f"⚠ Service account creation returned {service_response.status_code}: {service_response.text}"
        )
        print("  (This may be OK if the account already exists)")
    else:
        print("✓ Service account created")

    client.close()
    print("\n✅ PocketBase setup complete!")


if __name__ == "__main__":
    setup_pocketbase()
