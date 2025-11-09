"""
Tests for encryption service - critical security component.

Tests cover:
- Key generation (DEK, salt)
- Password-based key derivation (PBKDF2)
- AES-GCM encryption/decryption
- RSA key wrapping/unwrapping
- Field-level encryption
- Password change flows
"""

import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256

from priotag.services.encryption import EncryptionManager


@pytest.mark.unit
class TestKeyGeneration:
    """Test cryptographic key generation functions."""

    def test_generate_dek_returns_32_bytes(self):
        """DEK should be 32 bytes (256 bits) for AES-256."""
        dek = EncryptionManager.generate_dek()
        assert len(dek) == 32
        assert isinstance(dek, bytes)

    def test_generate_dek_unique(self):
        """Each DEK generation should produce unique keys."""
        dek1 = EncryptionManager.generate_dek()
        dek2 = EncryptionManager.generate_dek()
        assert dek1 != dek2

    def test_derive_key_from_password_returns_32_bytes(self):
        """Derived key should be 32 bytes."""
        salt = b"test_salt_16byte"
        password = "TestPassword123"
        key = EncryptionManager.derive_key_from_password(password, salt)
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_derive_key_deterministic(self):
        """Same password and salt should derive same key."""
        salt = b"test_salt_16byte"
        password = "TestPassword123"
        key1 = EncryptionManager.derive_key_from_password(password, salt)
        key2 = EncryptionManager.derive_key_from_password(password, salt)
        assert key1 == key2

    def test_derive_key_different_salts(self):
        """Different salts should produce different keys."""
        password = "TestPassword123"
        key1 = EncryptionManager.derive_key_from_password(password, b"salt_one_16bytes")
        key2 = EncryptionManager.derive_key_from_password(password, b"salt_two_16bytes")
        assert key1 != key2

    def test_derive_key_different_passwords(self):
        """Different passwords should produce different keys."""
        salt = b"test_salt_16byte"
        key1 = EncryptionManager.derive_key_from_password("Password1", salt)
        key2 = EncryptionManager.derive_key_from_password("Password2", salt)
        assert key1 != key2


@pytest.mark.unit
@pytest.mark.security
class TestAESEncryption:
    """Test AES-256-GCM encryption and decryption."""

    def test_encrypt_decrypt_roundtrip(self, test_dek):
        """Encrypt and decrypt should return original data."""
        original = "Test data to encrypt"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        decrypted = EncryptionManager.decrypt_data(encrypted, test_dek)
        assert decrypted == original

    def test_encrypted_data_is_different(self, test_dek):
        """Encrypted data should not equal original."""
        original = "Sensitive information"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        # Encrypted is base64, so decode to compare bytes
        assert encrypted != original
        assert base64.b64decode(encrypted) != original.encode()

    def test_encrypt_with_nonce_randomization(self, test_dek):
        """Same data encrypted twice should produce different ciphertexts."""
        original = "Test data"
        encrypted1 = EncryptionManager.encrypt_data(original, test_dek)
        encrypted2 = EncryptionManager.encrypt_data(original, test_dek)
        assert encrypted1 != encrypted2  # Different nonces

    def test_decrypt_with_wrong_key_fails(self, test_dek):
        """Decryption with wrong key should fail."""
        original = "Test data"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        wrong_dek = EncryptionManager.generate_dek()

        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure # AES-GCM authentication failure
            EncryptionManager.decrypt_data(encrypted, wrong_dek)

    def test_encrypt_empty_string(self, test_dek):
        """Empty string should be encrypted/decrypted correctly."""
        original = ""
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        decrypted = EncryptionManager.decrypt_data(encrypted, test_dek)
        assert decrypted == original

    def test_encrypt_unicode_data(self, test_dek):
        """Unicode characters should be handled correctly."""
        original = "Test with émojis 🔒 and ümlauts"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        decrypted = EncryptionManager.decrypt_data(encrypted, test_dek)
        assert decrypted == original

    def test_encrypted_data_is_base64(self, test_dek):
        """Encrypted data should be valid base64."""
        original = "Test data"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        # Should not raise exception
        decoded = base64.b64decode(encrypted)
        assert isinstance(decoded, bytes)

    def test_decrypt_invalid_base64_fails(self, test_dek):
        """Invalid base64 should raise appropriate error."""
        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.decrypt_data("not_valid_base64!!!", test_dek)

    def test_decrypt_tampered_data_fails(self, test_dek):
        """Tampered encrypted data should fail authentication."""
        original = "Test data"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)

        # Tamper with the encrypted data
        encrypted_bytes = base64.b64decode(encrypted)
        tampered = encrypted_bytes[:-1] + b"X"  # Change last byte
        tampered_b64 = base64.b64encode(tampered).decode()

        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure # GCM authentication failure
            EncryptionManager.decrypt_data(tampered_b64, test_dek)


@pytest.mark.unit
class TestFieldEncryption:
    """Test field-level encryption for dictionaries."""

    def test_encrypt_fields_dict(self, test_dek):
        """Dictionary should be encrypted as JSON."""
        data = {"name": "John Doe", "age": 30}
        encrypted = EncryptionManager.encrypt_fields(data, test_dek)
        assert isinstance(encrypted, str)
        assert encrypted != json.dumps(data)

    def test_decrypt_fields_roundtrip(self, test_dek):
        """Encrypt and decrypt dict should return original."""
        original = {"name": "Alice", "email": "alice@example.com"}
        encrypted = EncryptionManager.encrypt_fields(original, test_dek)
        decrypted = EncryptionManager.decrypt_fields(encrypted, test_dek)
        assert decrypted == original

    def test_encrypt_fields_preserves_types(self, test_dek):
        """Field types should be preserved after encryption/decryption."""
        original = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
        }
        encrypted = EncryptionManager.encrypt_fields(original, test_dek)
        decrypted = EncryptionManager.decrypt_fields(encrypted, test_dek)
        assert decrypted == original

    def test_encrypt_fields_nested_dict(self, test_dek):
        """Nested dictionaries should be handled correctly."""
        original = {"user": {"name": "Bob", "address": {"city": "Berlin"}}}
        encrypted = EncryptionManager.encrypt_fields(original, test_dek)
        decrypted = EncryptionManager.decrypt_fields(encrypted, test_dek)
        assert decrypted == original

    def test_decrypt_fields_invalid_json_fails(self, test_dek):
        """Invalid JSON after decryption should raise error."""
        # Encrypt non-JSON data
        encrypted = EncryptionManager.encrypt_data("not json data", test_dek)
        with pytest.raises(json.JSONDecodeError):
            EncryptionManager.decrypt_fields(encrypted, test_dek)


@pytest.mark.unit
@pytest.mark.security
class TestRSAKeyWrapping:
    """Test RSA key wrapping with admin public key."""

    def test_wrap_dek_with_admin_key(self, test_dek):
        """DEK should be wrapped with admin RSA public key."""
        wrapped = EncryptionManager.wrap_dek_with_admin_key(test_dek)
        assert isinstance(wrapped, str)
        assert len(wrapped) > 0
        # Wrapped should be base64
        decoded = base64.b64decode(wrapped)
        assert isinstance(decoded, bytes)

    def test_unwrap_dek_with_admin_private_key(self, test_dek, admin_rsa_keypair):
        """Wrapped DEK should be unwrappable with admin private key."""
        wrapped = EncryptionManager.wrap_dek_with_admin_key(test_dek)
        wrapped_bytes = base64.b64decode(wrapped)

        # Unwrap using private key
        unwrapped = admin_rsa_keypair["private_key"].decrypt(
            wrapped_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=SHA256()),
                algorithm=SHA256(),
                label=None,
            ),
        )
        assert unwrapped == test_dek

    def test_wrap_dek_unique_each_time(self, test_dek):
        """RSA-OAEP wrapping should produce different ciphertexts."""
        wrapped1 = EncryptionManager.wrap_dek_with_admin_key(test_dek)
        wrapped2 = EncryptionManager.wrap_dek_with_admin_key(test_dek)
        # Due to OAEP padding with random data, wrappings should differ
        assert wrapped1 != wrapped2


@pytest.mark.unit
class TestUserEncryptionDataCreation:
    """Test complete user encryption data creation."""

    def test_create_user_encryption_data(self, test_password):
        """Should create all required encryption data for new user."""
        result = EncryptionManager.create_user_encryption_data(test_password)

        # Check all required fields are present
        assert "salt" in result
        assert "user_wrapped_dek" in result
        assert "admin_wrapped_dek" in result

        # Check types and formats
        assert isinstance(result["salt"], str)
        assert isinstance(result["user_wrapped_dek"], str)
        assert isinstance(result["admin_wrapped_dek"], str)

        # Salt should be base64-encoded 16 bytes
        salt_bytes = base64.b64decode(result["salt"])
        assert len(salt_bytes) == 16
        # DEK should be unwrappable and be 32 bytes
        dek = EncryptionManager.get_user_dek(
            test_password, result["salt"], result["user_wrapped_dek"]
        )
        assert len(dek) == 32

    def test_created_dek_can_be_unwrapped(self, test_password):
        """User should be able to unwrap their DEK with password."""
        result = EncryptionManager.create_user_encryption_data(test_password)

        # Unwrap using password
        unwrapped_dek = EncryptionManager.get_user_dek(
            test_password, result["salt"], result["user_wrapped_dek"]
        )

        # Should be a valid 32-byte DEK
        assert len(unwrapped_dek) == 32
        assert isinstance(unwrapped_dek, bytes)

    def test_admin_can_unwrap_admin_wrapped_dek(self, test_password, admin_rsa_keypair):
        """Admin should be able to unwrap admin_wrapped_dek."""
        result = EncryptionManager.create_user_encryption_data(test_password)

        # Admin unwrap
        admin_wrapped_bytes = base64.b64decode(result["admin_wrapped_dek"])
        unwrapped = admin_rsa_keypair["private_key"].decrypt(
            admin_wrapped_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=SHA256()),
                algorithm=SHA256(),
                label=None,
            ),
        )

        # Should be a valid 32-byte DEK
        assert len(unwrapped) == 32
        assert isinstance(unwrapped, bytes)

        # Should be the same DEK as the user can unwrap
        user_unwrapped = EncryptionManager.get_user_dek(
            test_password, result["salt"], result["user_wrapped_dek"]
        )
        assert unwrapped == user_unwrapped


@pytest.mark.unit
@pytest.mark.security
class TestPasswordChange:
    """Test password change and DEK re-wrapping."""

    def test_change_password_preserves_dek(self, test_password):
        """DEK should remain the same after password change."""
        # Create initial encryption data
        initial_data = EncryptionManager.create_user_encryption_data(test_password)

        # Get original DEK
        original_dek = EncryptionManager.get_user_dek(
            test_password, initial_data["salt"], initial_data["user_wrapped_dek"]
        )

        # Change password
        new_password = "NewPassword456!"
        result = EncryptionManager.change_password(
            test_password,
            new_password,
            initial_data["salt"],
            initial_data["user_wrapped_dek"],
        )

        # Unwrap with new password
        unwrapped_dek = EncryptionManager.get_user_dek(
            new_password, result["salt"], result["user_wrapped_dek"]
        )
        assert unwrapped_dek == original_dek

    def test_change_password_new_salt(
        self,
        test_password,
    ):
        """Password change should generate new salt."""
        initial_data = EncryptionManager.create_user_encryption_data(test_password)

        new_password = "NewPassword456!"
        result = EncryptionManager.change_password(
            test_password,
            new_password,
            initial_data["salt"],
            initial_data["user_wrapped_dek"],
        )

        assert result["salt"] != initial_data["salt"]

    def test_old_password_fails_after_change(
        self,
        test_password,
    ):
        """Old password should not work after password change."""
        initial_data = EncryptionManager.create_user_encryption_data(test_password)

        new_password = "NewPassword456!"
        result = EncryptionManager.change_password(
            test_password,
            new_password,
            initial_data["salt"],
            initial_data["user_wrapped_dek"],
        )

        # Try to unwrap with old password - should fail
        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.get_user_dek(
                test_password, result["salt"], result["user_wrapped_dek"]
            )

    def test_encrypted_data_decryptable_after_password_change(
        self,
        test_password,
    ):
        """Data encrypted before password change should still be decryptable."""
        # Create initial data and encrypt something
        initial_data = EncryptionManager.create_user_encryption_data(test_password)

        # Get original DEK and encrypt something
        original_dek = EncryptionManager.get_user_dek(
            test_password, initial_data["salt"], initial_data["user_wrapped_dek"]
        )
        secret_data = {"message": "Secret information"}
        encrypted = EncryptionManager.encrypt_fields(secret_data, original_dek)

        # Change password
        new_password = "NewPassword456!"
        result = EncryptionManager.change_password(
            test_password,
            new_password,
            initial_data["salt"],
            initial_data["user_wrapped_dek"],
        )

        # Get DEK with new password
        unwrapped_dek = EncryptionManager.get_user_dek(
            new_password, result["salt"], result["user_wrapped_dek"]
        )

        # Decrypt old data with new DEK (should be same DEK)
        decrypted = EncryptionManager.decrypt_fields(encrypted, unwrapped_dek)
        assert decrypted == secret_data


@pytest.mark.unit
class TestGetUserDEK:
    """Test DEK unwrapping with password."""

    def test_get_user_dek_success(
        self,
        test_password,
    ):
        """Should successfully unwrap DEK with correct password."""
        data = EncryptionManager.create_user_encryption_data(test_password)
        dek = EncryptionManager.get_user_dek(
            test_password, data["salt"], data["user_wrapped_dek"]
        )

        # Should be a valid 32-byte DEK
        assert len(dek) == 32
        assert isinstance(dek, bytes)

    def test_get_user_dek_wrong_password_fails(
        self,
        test_password,
    ):
        """Wrong password should fail to unwrap DEK."""
        data = EncryptionManager.create_user_encryption_data(test_password)

        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.get_user_dek(
                "WrongPassword", data["salt"], data["user_wrapped_dek"]
            )

    def test_get_user_dek_wrong_salt_fails(
        self,
        test_password,
    ):
        """Wrong salt should fail to unwrap DEK."""
        data = EncryptionManager.create_user_encryption_data(test_password)

        wrong_salt = base64.b64encode(b"wrong_salt_16byt").decode()
        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.get_user_dek(
                test_password, wrong_salt, data["user_wrapped_dek"]
            )


@pytest.mark.security
class TestEncryptionSecurity:
    """Security-focused tests for encryption implementation."""

    def test_dek_not_stored_in_plaintext(
        self,
        test_password,
    ):
        """DEK should never be stored in plaintext."""
        result = EncryptionManager.create_user_encryption_data(test_password)

        # Unwrap the DEK to get its actual value
        dek = EncryptionManager.get_user_dek(
            test_password, result["salt"], result["user_wrapped_dek"]
        )

        # Check that plaintext DEK is not present in any wrapped form
        dek_b64 = base64.b64encode(dek).decode()
        assert dek_b64 not in result["user_wrapped_dek"]
        assert dek_b64 not in result["admin_wrapped_dek"]

        # Also verify that 'dek' key is not in the result
        assert "dek" not in result

    def test_password_not_stored(
        self,
        test_password,
    ):
        """Password should never appear in encryption data."""
        result = EncryptionManager.create_user_encryption_data(test_password)

        # Password should not be in any field
        for value in result.values():
            if isinstance(value, str):
                assert test_password not in value
                assert test_password.encode() not in base64.b64decode(value)

    def test_pbkdf2_iterations_sufficient(self):
        """PBKDF2 should use sufficient iterations (>=600000)."""
        # This is implicit in derive_key_from_password implementation
        # We test that derivation takes reasonable time (indicating many iterations)
        import time

        start = time.time()
        EncryptionManager.derive_key_from_password("password", b"salt_16_bytes!!!")
        duration = time.time() - start

        # With 600k iterations, this should take at least a few milliseconds
        assert duration > 0.001  # At least 1ms

    def test_aes_gcm_authentication(self, test_dek):
        """AES-GCM should provide authentication (detect tampering)."""
        original = "Important data"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        encrypted_bytes = base64.b64decode(encrypted)

        # Tamper with ciphertext (change one byte in the middle)
        tampered = bytearray(encrypted_bytes)
        tampered[len(tampered) // 2] ^= 0x01  # Flip one bit
        tampered_b64 = base64.b64encode(bytes(tampered)).decode()

        # Decryption should fail due to authentication tag mismatch
        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.decrypt_data(tampered_b64, test_dek)
