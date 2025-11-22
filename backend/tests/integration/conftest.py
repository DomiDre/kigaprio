"""
Pytest fixtures for integration tests.

Provides real Redis and PocketBase instances via testcontainers or docker-compose.
Set USE_DOCKER_SERVICES=true to use docker-compose services instead of testcontainers.
"""

import os
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
import redis
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

# Check if we should use docker-compose services
USE_DOCKER_SERVICES = os.getenv("USE_DOCKER_SERVICES", "").lower() == "true"

# Store setup results globally for session scope
_POCKETBASE_SETUP_RESULT = None


@pytest.fixture(scope="session")
def redis_container() -> Generator[DockerContainer | None, None, None]:
    """Start a Redis container for integration tests (or skip if using docker-compose)."""
    if USE_DOCKER_SERVICES:
        # Skip testcontainers, we'll use docker-compose services
        yield None
        return

    container = (
        DockerContainer("redis:8-alpine")
        .with_bind_ports("6379/tcp", 6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    )
    container.start()

    yield container

    container.stop()


@pytest.fixture(scope="session")
def redis_client(
    redis_container: DockerContainer | None,
) -> Generator[redis.Redis, None, None]:
    """Get a Redis client connected to the test container or docker-compose service."""
    if USE_DOCKER_SERVICES:
        from priotag.services import redis_service

        # Reset the singleton state to avoid stale cached URLs
        redis_service._redis_service._redis_url = None
        redis_service._redis_service._pool = None
        client = redis_service.get_redis()
    else:
        # Connect to testcontainer
        assert redis_container is not None, "redis container not loaded"
        client = redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=redis_container.get_exposed_port(6379),
            decode_responses=True,
        )

    # Wait for Redis to be ready
    for _ in range(30):
        try:
            client.ping()
            break
        except redis.ConnectionError:
            time.sleep(0.1)

    yield client

    if USE_DOCKER_SERVICES:
        # Clean up the singleton
        from priotag.services import redis_service

        redis_service.close_redis()
    else:
        client.close()


@pytest.fixture(scope="function")
def clean_redis(redis_client: redis.Redis) -> Generator[redis.Redis, None, None]:
    """Provide a clean Redis instance for each test."""
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()


def _setup_pocketbase(pocketbase_url: str) -> dict:
    """Set up PocketBase with required data (admin, institution, service account).

    Returns:
        dict: Contains 'institution' record and 'institution_keypair' with private key for testing
    """
    superuser_login = "admin@example.com"
    superuser_password = "admintest"

    # Wait for PocketBase to be ready
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
    assert (
        response.status_code == 200
    ), f"Failed to authenticate as admin: {response.status_code} - {response.text}"
    token = response.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    print("✓ Authenticated as admin")

    # Create default test institution
    print("Creating default test institution...")

    # Generate a test admin keypair for the institution (save for test use)
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    admin_public_key = public_pem.decode()

    institution_data = {
        "name": "Test Institution",
        "short_code": "TEST",
        "registration_magic_word": "test",
        "admin_public_key": admin_public_key,
        "active": True,
        "settings": {},
    }
    create_response = client.post(
        "/api/collections/institutions/records",
        json=institution_data,
    )
    assert (
        create_response.status_code == 200
    ), f"Failed to create institution: {create_response.status_code} - {create_response.text}"
    institution = create_response.json()
    print(
        f"✓ Institution created (id={institution['id']}, short_code={institution['short_code']})"
    )

    # Create service account
    from priotag.services import service_account

    print(f"Creating service account ({service_account.SERVICE_ACCOUNT_ID})...")
    service_response = client.post(
        "/api/collections/users/records",
        json={
            "username": service_account.SERVICE_ACCOUNT_ID,
            "password": service_account.SERVICE_ACCOUNT_PASSWORD,
            "passwordConfirm": service_account.SERVICE_ACCOUNT_PASSWORD,
            "role": "service",
            "institution_id": institution[
                "id"
            ],  # Associate service account with institution
        },
    )
    # Note: It's OK if this fails with 400 (duplicate) - the account may already exist
    if service_response.status_code == 200:
        print("✓ Service account created")
    else:
        print(
            f"  Service account creation returned {service_response.status_code} (may already exist)"
        )

    client.close()

    # Return institution and keypair for tests to use
    return {
        "institution": institution,
        "institution_keypair": {
            "private_key": private_key,
            "public_pem": public_pem,
            "private_pem": private_pem,
        },
    }


@pytest.fixture(scope="session")
def pocketbase_container(redis_client) -> Generator[DockerContainer | None, None, None]:
    """Start a PocketBase container for integration tests (or use docker-compose service)."""
    if USE_DOCKER_SERVICES:
        # Use docker-compose pocketbase service
        # NOTE: In docker-compose mode, PocketBase setup is handled by the CI script
        # (setup_pocketbase.py) before tests run, so we don't need to set it up here.
        yield None
        return

    # Start testcontainer
    superuser_login = "admin@example.com"
    superuser_password = "admintest"

    migrations_dir = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "pocketbase"
        / "pb_migrations"
    )

    print(f"Mounting migrations from: {migrations_dir}")
    print(f"Migrations exist: {migrations_dir.exists()}")
    if migrations_dir.exists():
        print(f"Migration files: {len(os.listdir(migrations_dir))}")

    container = (
        DockerContainer("ghcr.io/muchobien/pocketbase:latest")
        .with_bind_ports("8090/tcp", 8090)
        .with_env("PB_ADMIN_EMAIL", superuser_login)
        .with_env("PB_ADMIN_PASSWORD", superuser_password)
        .with_volume_mapping(migrations_dir, "/pb_migrations", mode="ro")
        .waiting_for(LogMessageWaitStrategy("Server started"))
    )
    container.start()

    host = container.get_container_host_ip()
    port = container.get_exposed_port(8090)
    pocketbase_url = f"http://{host}:{port}"

    # Store setup result globally for access by fixtures
    global _POCKETBASE_SETUP_RESULT
    _POCKETBASE_SETUP_RESULT = _setup_pocketbase(pocketbase_url)

    yield container

    container.stop()


@pytest.fixture(scope="function")
def pocketbase_url(monkeypatch, pocketbase_container):
    from priotag.services import pocketbase_service, service_account

    if USE_DOCKER_SERVICES:
        pocketbase_url = pocketbase_service.POCKETBASE_URL
    else:
        host = pocketbase_container.get_container_host_ip()
        port = pocketbase_container.get_exposed_port(8090)
        pocketbase_url = f"http://{host}:{port}"
        monkeypatch.setattr(pocketbase_service, "POCKETBASE_URL", pocketbase_url)
        # Also patch service_account module which imports POCKETBASE_URL directly
        monkeypatch.setattr(service_account, "POCKETBASE_URL", pocketbase_url)

        # Patch all route modules that import POCKETBASE_URL directly
        # This is necessary because Python imports create local copies of the constant
        try:
            from priotag.api.routes import account, auth, priorities, vacation_days
            from priotag.services import institution

            monkeypatch.setattr(priorities, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(vacation_days, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(account, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(auth, "POCKETBASE_URL", pocketbase_url)
            monkeypatch.setattr(institution, "POCKETBASE_URL", pocketbase_url)
        except (ImportError, AttributeError):
            # Modules may not be imported yet
            pass

    return pocketbase_url


@pytest.fixture(scope="session")
def test_institution_keypair(pocketbase_container):
    """
    Get the test institution's admin keypair for integration tests.

    This keypair can be used to decrypt admin_wrapped_dek fields in tests.
    Returns None in docker-compose mode (keypair not available).
    """
    if USE_DOCKER_SERVICES:
        # In docker-compose mode, we don't have access to the keypair
        return None

    global _POCKETBASE_SETUP_RESULT
    if _POCKETBASE_SETUP_RESULT is None:
        return None

    return _POCKETBASE_SETUP_RESULT.get("institution_keypair")


@pytest.fixture(scope="function")
def pocketbase_admin_client(pocketbase_url: str) -> Generator[httpx.Client, None, None]:
    """
    Create an authenticated admin client for PocketBase.

    Sets up an admin user and returns an authenticated client.
    """
    client = httpx.Client(base_url=pocketbase_url, timeout=10.0)

    # Create admin user (PocketBase in --dev mode allows this)
    superuser_login = "admin@example.com"
    superuser_password = "admintest"

    response = client.post(
        "/api/collections/_superusers/auth-with-password",
        json={
            "identity": superuser_login,
            "password": superuser_password,
        },
    )
    assert response.status_code == 200
    response_body = response.json()
    token = response_body["token"]

    client.headers["Authorization"] = f"Bearer {token}"

    yield client

    client.close()


@pytest.fixture(scope="function", autouse=True)
def reset_redis_singleton():
    """
    Reset Redis service singleton state before each integration test.

    This is necessary because unit tests may have already imported and
    initialized the redis_service module, leaving stale state.
    """
    from priotag.services import redis_service

    # Reset singleton state
    redis_service._redis_service._redis_url = None
    redis_service._redis_service._pool = None

    yield

    # Clean up after test
    redis_service.close_redis()


def register_and_login_user(
    test_app,
    username: str | None = None,
    password: str | None = None,
    name: str | None = None,
) -> dict:
    """
    Helper function to register and login a test user.

    Args:
        test_app: FastAPI TestClient
        username: Username for the user (auto-generated if not provided)
        password: Password for the user (default: "SecurePassword123!")
        name: Display name for the user (default: "Test User")

    Returns:
        dict with:
            - username: The username used
            - password: The password used
            - name: The display name used
            - cookies: Authentication cookies from login
            - user_record: The user record from registration
    """
    import secrets

    # Generate unique username if not provided
    if username is None:
        unique_suffix = secrets.token_hex(4)
        username = f"testuser_{unique_suffix}"

    user_data: dict[str, str | dict] = {
        "username": username,
        "password": password or "SecurePassword123!",
        "name": name or "Test User",
        "magic_word": "test",  # Default test institution magic word
        "institution_short_code": "TEST",  # Default test institution
    }

    # Verify magic word
    verify_response = test_app.post(
        "/api/v1/auth/verify-magic-word",
        json={
            "magic_word": user_data["magic_word"],
            "institution_short_code": user_data["institution_short_code"],
        },
    )
    assert (
        verify_response.status_code == 200
    ), f"Failed to verify magic word: {verify_response.status_code} - {verify_response.text}"
    magic_word_body = verify_response.json()
    user_data["reg_token"] = magic_word_body["token"]

    # Register user
    register_response = test_app.post(
        "/api/v1/auth/register",
        json={
            "identity": user_data["username"],
            "password": user_data["password"],
            "passwordConfirm": user_data["password"],
            "name": user_data["name"],
            "registration_token": user_data["reg_token"],
        },
    )
    assert (
        register_response.status_code == 200
    ), f"Failed to register user: {register_response.status_code} - {register_response.text}"
    register_body = register_response.json()
    if "record" in register_body:
        user_data["user_record"] = register_body["record"]

    # Login
    login_response = test_app.post(
        "/api/v1/auth/login",
        json={
            "identity": user_data["username"],
            "password": user_data["password"],
        },
    )
    assert (
        login_response.status_code == 200
    ), f"Failed to login: {login_response.status_code} - {login_response.text}"
    user_data["cookies"] = dict(login_response.cookies)

    return user_data


@pytest.fixture(scope="function")
def test_app(pocketbase_url: str, clean_redis: redis.Redis):
    """
    Create a FastAPI test application with real dependencies.

    Uses the real PocketBase and Redis containers.
    """
    # Import app fresh to avoid stale state from unit tests
    import sys

    from fastapi.testclient import TestClient

    from priotag.services.redis_service import get_redis

    # Remove cached module if it exists
    if "priotag.main" in sys.modules:
        del sys.modules["priotag.main"]

    # Import fresh app instance
    from priotag.main import app

    # Override get_redis dependency BEFORE creating TestClient
    # This ensures the dependency override is in place before lifespan runs
    if not USE_DOCKER_SERVICES:

        def get_test_redis():
            return clean_redis

        app.dependency_overrides[get_redis] = get_test_redis

    # Create test client (this triggers lifespan startup)
    # NOTE: raise_server_exceptions=False to avoid masking the actual HTTP error
    client = TestClient(app, raise_server_exceptions=False)

    yield client

    # Clean up dependency overrides
    if not USE_DOCKER_SERVICES:
        app.dependency_overrides.clear()
