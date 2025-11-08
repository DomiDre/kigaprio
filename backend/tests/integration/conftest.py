"""
Pytest fixtures for integration tests.

Provides real Redis and PocketBase instances via testcontainers.
"""

import os
import time
from pathlib import Path
from typing import Generator

import httpx
import requests
import pytest
import redis
import asyncio
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.redis import RedisContainer


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    """Start a Redis container for integration tests."""
    container = RedisContainer("redis:8-alpine")
    container.start()

    yield container

    container.stop()


@pytest.fixture(scope="session")
def redis_client(redis_container: RedisContainer) -> Generator[redis.Redis, None, None]:
    """Get a Redis client connected to the test container."""
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

    client.close()


@pytest.fixture(scope="function")
def clean_redis(redis_client: redis.Redis) -> Generator[redis.Redis, None, None]:
    """Provide a clean Redis instance for each test."""
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()


@pytest.fixture(scope="session")
def pocketbase_container(redis_client) -> Generator[DockerContainer, None, None]:
    """Start a PocketBase container for integration tests."""
    superuser_login = "admin@example.com"
    superuser_password = "admintest"

    # Get the path to the migrations directory (relative to backend/tests/integration/)
    # Go up to backend/ then to ../pocketbase/pb_migrations
    migrations_dir = Path(__file__).resolve().parent.parent.parent.parent / "pocketbase" / "pb_migrations"

    print(f"Mounting migrations from: {migrations_dir}")
    print(f"Migrations exist: {migrations_dir.exists()}")
    if migrations_dir.exists():
        print(f"Migration files: {len(os.listdir(migrations_dir))}")

    container = (
        DockerContainer("ghcr.io/muchobien/pocketbase:latest")
        .with_bind_ports("8090/tcp", 8090)
        .with_env("PB_ADMIN_EMAIL", superuser_login)
        .with_env("PB_ADMIN_PASSWORD", superuser_password)
        .with_volume_mapping(migrations_dir, "/pb_migrations", mode="ro")  # PocketBase expects migrations in /pb/pb_migrations
    )
    container.start()
    wait_for_logs(container, ".*Server started.*")

    # Wait for PocketBase to be ready
    host = container.get_container_host_ip()
    port = container.get_exposed_port(8090)
    pocketbase_url = f"http://{host}:{port}"

    client = httpx.Client(base_url=pocketbase_url, timeout=10.0)
    superuser_login = "admin@example.com"
    superuser_password = "admintest"
    magic_word = "test"

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


    create_response = client.post(
        "/api/collections/system_settings/records",
        json={
            "key": "registration_magic_word",
            "value": magic_word,
            "description": "Magic word required for user registration",
            "last_updated_by": superuser_login
        },
    )
    assert create_response.status_code == 200

    # Create service account
    from kigaprio.services import service_account
    response = client.post(
        "/api/collections/users/records",
        json={
            "username": service_account.SERVICE_ACCOUNT_ID,
            "password": service_account.SERVICE_ACCOUNT_PASSWORD,
            "passwordConfirm": service_account.SERVICE_ACCOUNT_PASSWORD,
            "role": "service",
        }
    )

    for _ in range(60):  # Wait up to 60 seconds
        try:
            response = httpx.get(f"{pocketbase_url}/api/health", timeout=1.0)
            if response.status_code == 200:
                break
        except (httpx.RequestError, httpx.TimeoutException):
            time.sleep(1)

    yield container

    container.stop()


@pytest.fixture(scope="function")
def pocketbase_url(monkeypatch, pocketbase_container):
    host = pocketbase_container.get_container_host_ip()
    port = pocketbase_container.get_exposed_port(8090)
    pocketbase_url = f"http://{host}:{port}"

    from kigaprio.services import pocketbase_service
    monkeypatch.setattr(pocketbase_service, "POCKETBASE_URL", pocketbase_url)
    return pocketbase_url



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


@pytest.fixture(scope="function")
def test_app(pocketbase_url: str, clean_redis: redis.Redis):
    """
    Create a FastAPI test application with real dependencies.

    Uses the real PocketBase and Redis containers.
    """
    from fastapi.testclient import TestClient

    # Set environment variables for the app
    os.environ["POCKETBASE_URL"] = pocketbase_url
    os.environ["REDIS_HOST"] = clean_redis.connection_pool.connection_kwargs["host"]
    os.environ["REDIS_PORT"] = str(clean_redis.connection_pool.connection_kwargs["port"])

    # Import main app after setting env vars
    from kigaprio.main import app

    # Override get_redis to use our test Redis
    from kigaprio.services.redis_service import get_redis

    def override_get_redis():
        return clean_redis

    app.dependency_overrides[get_redis] = override_get_redis

    client = TestClient(app)

    yield client

    # Cleanup
    app.dependency_overrides.clear()
