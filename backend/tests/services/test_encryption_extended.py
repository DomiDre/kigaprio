"""
Extended tests for encryption service to increase coverage.

Tests cover:
- DEK splitting and reconstruction (balanced security mode)
- DEK part encryption/decryption for caching
- get_dek_from_request for different security tiers
- get_user_data and handle_password_change helper functions
"""

import base64
import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from priotag.services.encryption import (
    EncryptionManager,
    get_user_data,
    handle_password_change,
)


@pytest.mark.unit
class TestDEKSplitting:
    """Test DEK splitting for balanced security mode."""

    def test_split_dek_returns_two_parts(self, test_dek):
        """Should split DEK into two parts."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)

        assert isinstance(server_part, str)
        assert isinstance(client_part, str)
        assert server_part != client_part

    def test_split_dek_parts_are_base64(self, test_dek):
        """Split parts should be valid base64."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)

        # Should decode without error
        server_bytes = base64.b64decode(server_part)
        client_bytes = base64.b64decode(client_part)

        assert isinstance(server_bytes, bytes)
        assert isinstance(client_bytes, bytes)

    def test_split_dek_parts_same_length_as_dek(self, test_dek):
        """Split parts should be same length as original DEK."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)

        server_bytes = base64.b64decode(server_part)
        client_bytes = base64.b64decode(client_part)

        assert len(server_bytes) == len(test_dek)
        assert len(client_bytes) == len(test_dek)

    def test_split_dek_unique_each_time(self, test_dek):
        """Split should produce different parts each time (due to random server part)."""
        server1, client1 = EncryptionManager.split_dek(test_dek)
        server2, client2 = EncryptionManager.split_dek(test_dek)

        # Server parts should be different (random)
        assert server1 != server2
        # Client parts should also be different (due to XOR with different server)
        assert client1 != client2

    def test_reconstruct_dek_from_parts(self, test_dek):
        """Should reconstruct original DEK from split parts."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)
        reconstructed = EncryptionManager.reconstruct_dek(server_part, client_part)

        assert reconstructed == test_dek

    def test_reconstruct_dek_wrong_parts_fails(self, test_dek):
        """Reconstructing with wrong parts should not give original DEK."""
        server_part1, client_part1 = EncryptionManager.split_dek(test_dek)
        server_part2, _ = EncryptionManager.split_dek(test_dek)

        # Mix parts from different splits
        wrong_reconstruction = EncryptionManager.reconstruct_dek(
            server_part2, client_part1
        )

        assert wrong_reconstruction != test_dek


@pytest.mark.unit
class TestDEKPartEncryption:
    """Test encryption of DEK parts for caching."""

    @pytest.fixture(autouse=True)
    def setup_server_cache_key(self):
        """Ensure server cache key is initialized for all tests."""
        # Save original value
        original_key = EncryptionManager._SERVER_CACHE_KEY
        # Set a valid 32-byte key for testing
        EncryptionManager._SERVER_CACHE_KEY = b"test_server_cache_key_32bytes!!!"  # Exactly 32 bytes
        yield
        # Restore original value (important for integration tests)
        EncryptionManager._SERVER_CACHE_KEY = original_key

    def test_encrypt_dek_part(self):
        """Should encrypt DEK part."""
        dek_part = base64.b64encode(b"test_dek_part_32bytes_long!!!").decode()
        encrypted = EncryptionManager.encrypt_dek_part(dek_part)

        assert isinstance(encrypted, str)
        assert encrypted != dek_part

    def test_decrypt_dek_part(self):
        """Should decrypt encrypted DEK part."""
        dek_part = base64.b64encode(b"test_dek_part_32bytes_long!!!").decode()
        encrypted = EncryptionManager.encrypt_dek_part(dek_part)
        decrypted = EncryptionManager.decrypt_dek_part(encrypted)

        assert decrypted == dek_part

    def test_encrypt_decrypt_dek_part_roundtrip(self, test_dek):
        """Encrypt and decrypt DEK part should preserve data."""
        server_part, _ = EncryptionManager.split_dek(test_dek)

        encrypted = EncryptionManager.encrypt_dek_part(server_part)
        decrypted = EncryptionManager.decrypt_dek_part(encrypted)

        assert decrypted == server_part

    def test_encrypt_dek_part_uses_server_cache_key(self):
        """Should use server cache key for encryption."""
        with patch.object(
            EncryptionManager, "_get_server_cache_key"
        ) as mock_get_key:
            mock_get_key.return_value = b"test_server_cache_key_32bytes!!!"  # Exactly 32 bytes
            dek_part = base64.b64encode(b"test_part").decode()

            EncryptionManager.encrypt_dek_part(dek_part)

            # Should have called _get_server_cache_key
            mock_get_key.assert_called_once()


@pytest.mark.unit
class TestGetDekFromRequest:
    """Test DEK reconstruction from request based on security tier."""

    @pytest.fixture(autouse=True)
    def setup_server_cache_key(self):
        """Ensure server cache key is initialized for all tests."""
        # Save original value
        original_key = EncryptionManager._SERVER_CACHE_KEY
        # Set a valid 32-byte key for testing
        EncryptionManager._SERVER_CACHE_KEY = b"test_server_cache_key_32bytes!!!"  # Exactly 32 bytes
        yield
        # Restore original value (important for integration tests)
        EncryptionManager._SERVER_CACHE_KEY = original_key

    def test_get_dek_high_security_mode(self, test_dek, fake_redis):
        """High security mode should decode DEK directly from request."""
        dek_b64 = base64.b64encode(test_dek).decode()

        result = EncryptionManager.get_dek_from_request(
            dek_or_client_part=dek_b64,
            user_id="user123",
            token="token123",
            security_tier="high",
            redis_client=fake_redis,
        )

        assert result == test_dek

    def test_get_dek_convenience_mode(self, test_dek, fake_redis):
        """Convenience mode should decode DEK directly from request."""
        dek_b64 = base64.b64encode(test_dek).decode()

        result = EncryptionManager.get_dek_from_request(
            dek_or_client_part=dek_b64,
            user_id="user123",
            token="token123",
            security_tier="convenience",
            redis_client=fake_redis,
        )

        assert result == test_dek

    def test_get_dek_balanced_mode_with_cache(self, test_dek, fake_redis):
        """Balanced mode should reconstruct DEK from cached server part and client part."""
        # Split DEK
        server_part, client_part = EncryptionManager.split_dek(test_dek)

        # Encrypt server part for cache
        encrypted_server_part = EncryptionManager.encrypt_dek_part(server_part)

        # Cache the encrypted server part
        cache_key = "dek:user123:token123"
        cache_data = {
            "encrypted_server_part": encrypted_server_part,
            "last_accessed": datetime.now().isoformat(),
        }
        fake_redis.setex(cache_key, 1800, json.dumps(cache_data))

        # Reconstruct DEK
        result = EncryptionManager.get_dek_from_request(
            dek_or_client_part=client_part,
            user_id="user123",
            token="token123",
            security_tier="balanced",
            redis_client=fake_redis,
        )

        assert result == test_dek

    def test_get_dek_balanced_mode_cache_miss(self, fake_redis):
        """Balanced mode should raise error when cache is missing."""
        with pytest.raises(ValueError) as exc_info:
            EncryptionManager.get_dek_from_request(
                dek_or_client_part="client_part_base64",
                user_id="user123",
                token="token123",
                security_tier="balanced",
                redis_client=fake_redis,
            )

        assert "DEK cache expired" in str(exc_info.value)

    def test_get_dek_balanced_mode_updates_cache_ttl(self, test_dek, fake_redis):
        """Balanced mode should update cache TTL on access."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)
        encrypted_server_part = EncryptionManager.encrypt_dek_part(server_part)

        cache_key = "dek:user123:token123"
        cache_data = {
            "encrypted_server_part": encrypted_server_part,
            "last_accessed": "2024-01-01T00:00:00",
        }
        fake_redis.setex(cache_key, 1800, json.dumps(cache_data))

        # Access DEK
        EncryptionManager.get_dek_from_request(
            dek_or_client_part=client_part,
            user_id="user123",
            token="token123",
            security_tier="balanced",
            redis_client=fake_redis,
        )

        # Cache should be updated
        updated_cache = json.loads(fake_redis.get(cache_key))
        assert updated_cache["last_accessed"] != "2024-01-01T00:00:00"
        # Should have new timestamp
        assert datetime.fromisoformat(updated_cache["last_accessed"]).year >= 2025


@pytest.mark.unit
class TestHelperFunctions:
    """Test module-level helper functions."""

    def test_get_user_data(self, test_password):
        """Should decrypt user data using password."""
        # Create encryption data
        encryption_data = EncryptionManager.create_user_encryption_data(test_password)

        # Get DEK and encrypt some fields
        dek = EncryptionManager.get_user_dek(
            test_password, encryption_data["salt"], encryption_data["user_wrapped_dek"]
        )

        user_fields = {"name": "John Doe", "email": "john@example.com"}
        encrypted_fields = EncryptionManager.encrypt_fields(user_fields, dek)

        # Create user record
        user_record = {
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
            "encrypted_fields": encrypted_fields,
        }

        # Get user data
        result = get_user_data(test_password, user_record)

        assert result == user_fields

    def test_get_user_data_wrong_password_fails(self, test_password):
        """Should fail to decrypt with wrong password."""
        encryption_data = EncryptionManager.create_user_encryption_data(test_password)

        dek = EncryptionManager.get_user_dek(
            test_password, encryption_data["salt"], encryption_data["user_wrapped_dek"]
        )

        user_fields = {"name": "Jane Doe"}
        encrypted_fields = EncryptionManager.encrypt_fields(user_fields, dek)

        user_record = {
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
            "encrypted_fields": encrypted_fields,
        }

        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            get_user_data("WrongPassword", user_record)

    def test_handle_password_change(self, test_password):
        """Should handle password change and return updated encryption data."""
        # Create initial user record
        encryption_data = EncryptionManager.create_user_encryption_data(test_password)

        user_record = {
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
        }

        new_password = "NewSecurePassword123!"

        # Handle password change
        result = handle_password_change(test_password, new_password, user_record)

        # Should return new salt and user_wrapped_dek
        assert "salt" in result
        assert "user_wrapped_dek" in result
        assert result["salt"] != user_record["salt"]

        # Should be able to unwrap DEK with new password
        new_dek = EncryptionManager.get_user_dek(
            new_password, result["salt"], result["user_wrapped_dek"]
        )
        assert len(new_dek) == 32

    def test_handle_password_change_preserves_dek(self, test_password):
        """Password change should preserve the same DEK."""
        encryption_data = EncryptionManager.create_user_encryption_data(test_password)

        user_record = {
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
        }

        # Get original DEK
        original_dek = EncryptionManager.get_user_dek(
            test_password, user_record["salt"], user_record["user_wrapped_dek"]
        )

        new_password = "NewPassword456!"
        result = handle_password_change(test_password, new_password, user_record)

        # Get new DEK
        new_dek = EncryptionManager.get_user_dek(
            new_password, result["salt"], result["user_wrapped_dek"]
        )

        # Should be the same DEK
        assert new_dek == original_dek


@pytest.mark.unit
class TestServerCacheKey:
    """Test server cache key management."""

    def test_get_server_cache_key_generates_if_not_exists(self):
        """Should generate ephemeral key if secret file doesn't exist."""
        EncryptionManager._SERVER_CACHE_KEY = None

        with patch("pathlib.Path.exists", return_value=False):
            key = EncryptionManager._get_server_cache_key()

            assert isinstance(key, bytes)
            assert len(key) == 32

    def test_get_server_cache_key_loads_from_secret(self):
        """Should load key from secret file if it exists."""
        EncryptionManager._SERVER_CACHE_KEY = None
        test_key = b"test_server_cache_key_32byte!!"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_bytes", return_value=test_key):
                key = EncryptionManager._get_server_cache_key()

                assert key == test_key

    def test_get_server_cache_key_caches_result(self):
        """Should cache the key after first access."""
        EncryptionManager._SERVER_CACHE_KEY = None

        with patch("pathlib.Path.exists", return_value=False):
            key1 = EncryptionManager._get_server_cache_key()
            key2 = EncryptionManager._get_server_cache_key()

            # Should return same key (cached)
            assert key1 == key2
