"""
Pytest configuration and shared fixtures for PrioTag backend tests.
"""

import base64
import os
from unittest.mock import AsyncMock

import fakeredis
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture
def fake_redis():
    """Provide a fake Redis client for testing."""
    # Use decode_responses=True to match production Redis configuration
    # Production code expects strings, not bytes
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_redis_client(fake_redis):
    """Mock Redis client that uses fakeredis."""
    return fake_redis


@pytest.fixture
def mock_pocketbase_client():
    """Mock PocketBase HTTP client."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.patch = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def admin_rsa_keypair():
    """Generate RSA keypair for admin encryption testing."""
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

    return {
        "private_key": private_key,
        "public_pem": public_pem,
        "private_pem": private_pem,
    }


@pytest.fixture
def test_secrets_dir(tmp_path, admin_rsa_keypair):
    """Create temporary secrets directory with test secrets."""
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()

    # Write admin public key
    (secrets_dir / "admin_public_key.pem").write_bytes(admin_rsa_keypair["public_pem"])

    # Write other secrets
    (secrets_dir / "redis_pass").write_text("test_redis_password")
    (secrets_dir / "server_cache_key").write_text("test_cache_key_32_bytes_long_!!")
    (secrets_dir / "pb_service_id").write_text("test_service")
    (secrets_dir / "pb_service_password").write_text("test_service_password")
    (secrets_dir / "metrics_token").write_text("test_metrics_token")

    return secrets_dir


@pytest.fixture(autouse=True)
def mock_admin_key(monkeypatch, admin_rsa_keypair, tmp_path):
    """Mock the admin public key file path for all tests."""
    # Create temporary secrets directory
    secrets_dir = tmp_path / "run" / "secrets"
    secrets_dir.mkdir(parents=True)

    # Write admin public key
    admin_key_file = secrets_dir / "admin_public_key.pem"
    admin_key_file.write_bytes(admin_rsa_keypair["public_pem"])

    # Write server cache key
    cache_key_file = secrets_dir / "server_cache_key"
    cache_key_file.write_bytes(b"test_cache_key_32_bytes_long_!!")

    # Write redis password (needed for RedisService)
    redis_pass_file = secrets_dir / "redis_pass"
    redis_pass_file.write_text("test_redis_password")

    # Mock the Path objects in EncryptionManager
    from priotag.services.encryption import EncryptionManager

    # Save original values
    original_admin_key = EncryptionManager.ADMIN_PUBLIC_KEY_PEM
    original_cache_key = EncryptionManager._SERVER_CACHE_KEY

    # Set test values
    EncryptionManager.ADMIN_PUBLIC_KEY_PEM = admin_rsa_keypair["public_pem"]
    EncryptionManager._SERVER_CACHE_KEY = b"test_cache_key_32_bytes_long_!!"

    yield

    # Restore original values (important for integration tests)
    EncryptionManager.ADMIN_PUBLIC_KEY_PEM = original_admin_key
    EncryptionManager._SERVER_CACHE_KEY = original_cache_key


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "test_user_123",
        "username": "testuser",
        "email": "test@example.com",
        "emailVisibility": False,
        "role": "user",
        "salt": base64.b64encode(b"test_salt_16bytes").decode(),
        "user_wrapped_dek": base64.b64encode(b"wrapped_dek_data").decode(),
        "admin_wrapped_dek": base64.b64encode(b"admin_wrapped_dek").decode(),
        "encrypted_fields": base64.b64encode(b'{"name":"encrypted_name"}').decode(),
        "lastSeen": "2025-01-08T10:00:00Z",
        "verified": True,
        "collectionId": "users_collection_id",
        "collectionName": "users",
        "created": "2025-01-01T00:00:00Z",
        "updated": "2025-01-08T00:00:00Z",
    }


@pytest.fixture
def sample_admin_data():
    """Sample admin user data for testing."""
    return {
        "id": "admin_user_456",
        "username": "admin",
        "email": "admin@example.com",
        "emailVisibility": False,
        "role": "admin",
        "salt": base64.b64encode(b"admin_salt_16byt").decode(),
        "user_wrapped_dek": base64.b64encode(b"admin_wrapped_dek_data").decode(),
        "admin_wrapped_dek": base64.b64encode(b"admin_admin_wrapped").decode(),
        "encrypted_fields": base64.b64encode(b'{"name":"Admin User"}').decode(),
        "lastSeen": "2025-01-08T12:00:00Z",
        "verified": True,
        "collectionId": "users_collection_id",
        "collectionName": "users",
        "created": "2025-01-01T00:00:00Z",
        "updated": "2025-01-08T12:00:00Z",
    }


@pytest.fixture
def sample_priority_data():
    """Sample priority data for testing."""
    return {
        "id": "priority_123",
        "userId": "test_user_123",
        "month": "2025-01",
        "weeks": [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            },
            {
                "weekNumber": 2,
                "monday": 2,
                "tuesday": 3,
                "wednesday": 4,
                "thursday": 5,
                "friday": 1,
            },
        ],
        "encrypted_fields": "",
        "identifier": "",
        "manual": False,
        "collectionId": "priorities_collection_id",
        "collectionName": "priorities",
        "created": "2025-01-01T00:00:00Z",
        "updated": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_session_info():
    """Sample session info for testing."""
    from priotag.models.auth import SessionInfo

    return SessionInfo(
        id="test_user_123",
        username="testuser",
        is_admin=False,
    )


@pytest.fixture
def sample_admin_session_info():
    """Sample admin session info for testing."""
    from priotag.models.auth import SessionInfo

    return SessionInfo(
        id="admin_user_456",
        username="admin",
        is_admin=True,
    )


@pytest.fixture
def test_dek():
    """Generate a test Data Encryption Key."""
    from priotag.services.encryption import EncryptionManager

    return EncryptionManager.generate_dek()


@pytest.fixture
def test_password():
    """Test password for encryption tests."""
    return "TestPassword123!"


@pytest.fixture
def mock_get_redis(fake_redis):
    """Mock the get_redis dependency to return fake Redis."""

    def _mock_get_redis():
        return fake_redis

    return _mock_get_redis


@pytest.fixture
def authenticated_headers():
    """Sample authenticated request headers."""
    return {"Cookie": "auth_token=test_token_value; dek=test_dek_base64"}


@pytest.fixture
def mock_verify_token(sample_session_info):
    """Mock verify_token dependency."""

    async def _mock_verify_token():
        return sample_session_info

    return _mock_verify_token


@pytest.fixture
def mock_require_admin(sample_admin_session_info):
    """Mock require_admin dependency."""

    async def _mock_require_admin():
        return sample_admin_session_info

    return _mock_require_admin


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for external API calls."""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.patch = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def reset_environment(request):
    """Reset environment variables after unit tests only (not integration tests)."""
    # Skip this fixture for integration tests to avoid interfering with their environment setup
    is_integration_test = "integration" in request.keywords or "integration" in str(
        request.fspath
    )

    if is_integration_test:
        yield
        return

    # Only reset environment for unit tests
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
