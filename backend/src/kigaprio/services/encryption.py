"""Field-level encryption system allowing for password changes by using data encryption keys"""

import base64
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionManager:
    """Manages field-level encryption for sensitive user data."""

    ADMIN_PUBLIC_KEY_PEM = Path("/run/secrets/admin_public_key").read_bytes()

    KDF_ITERATIONS = 600000
    KEY_SIZE = 32

    @staticmethod
    def generate_dek() -> bytes:
        """Generate a new Data Encryption Key (DEK) for a user."""
        return AESGCM.generate_key(bit_length=256)

    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        """
        Derive an encryption key from a password using PBKDF2.

        Args:
            password: User's password
            salt: Unique salt for this user (store in PocketBase)

        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=EncryptionManager.KEY_SIZE,
            salt=salt,
            iterations=EncryptionManager.KDF_ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())

    @staticmethod
    def encrypt_data(data: str, key: bytes) -> str:
        """
        Encrypt data using AES-GCM.

        Args:
            data: Plaintext string to encrypt
            key: 32-byte encryption key

        Returns:
            Base64-encoded: nonce + ciphertext + tag
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96 bits for GCM
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)

        # Combine nonce + ciphertext and encode
        encrypted = nonce + ciphertext
        return base64.b64encode(encrypted).decode()

    @staticmethod
    def decrypt_data(encrypted_data: str, key: bytes) -> str:
        """
        Decrypt data using AES-GCM.

        Args:
            encrypted_data: Base64-encoded encrypted data
            key: 32-byte decryption key

        Returns:
            Decrypted plaintext string
        """
        encrypted = base64.b64decode(encrypted_data)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()

    @classmethod
    def _load_admin_public_key(cls) -> RSAPublicKey:
        """Load admin's RSA public key."""
        public_key = serialization.load_pem_public_key(
            cls.ADMIN_PUBLIC_KEY_PEM, backend=default_backend()
        )
        # Type check and cast
        if not isinstance(public_key, RSAPublicKey):
            raise TypeError(f"Expected RSA public key, got {type(public_key)}")

        return public_key

    @classmethod
    def wrap_dek_with_admin_key(cls, dek: bytes) -> str:
        """
        Wrap DEK with admin's PUBLIC key.
        Server can do this, but CANNOT unwrap!
        """
        public_key = cls._load_admin_public_key()

        encrypted_dek = public_key.encrypt(
            dek,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return base64.b64encode(encrypted_dek).decode()

    @classmethod
    def create_user_encryption_data(cls, password: str) -> dict[str, str]:
        """
        Create encryption data for a new user.

        Args:
            password: User's password

        Returns:
            Dictionary with keys to store in PocketBase:
            - salt: Base64-encoded salt for password KDF
            - user_wrapped_dek: DEK encrypted with user's password-derived key
            - admin_wrapped_dek: DEK encrypted with admin master key
        """
        # Generate salt and DEK
        salt = os.urandom(16)
        dek = cls.generate_dek()

        # Derive key from password
        password_key = cls.derive_key_from_password(password, salt)

        # Encrypt DEK with password-derived key
        user_wrapped_dek = cls.encrypt_data(
            base64.b64encode(dek).decode(), password_key
        )

        # Encrypt DEK with admin public key for external decryption using private key
        admin_wrapped_dek = cls.wrap_dek_with_admin_key(dek)

        return {
            "salt": base64.b64encode(salt).decode(),
            "user_wrapped_dek": user_wrapped_dek,
            "admin_wrapped_dek": admin_wrapped_dek,
        }

    @classmethod
    def get_user_dek(cls, password: str, salt: str, user_wrapped_dek: str) -> bytes:
        """
        Retrieve user's DEK using their password.

        Args:
            password: User's password
            salt: Base64-encoded salt from PocketBase
            user_wrapped_dek: Encrypted DEK from PocketBase

        Returns:
            Decrypted DEK
        """
        salt_bytes = base64.b64decode(salt)
        password_key = cls.derive_key_from_password(password, salt_bytes)
        dek_b64 = cls.decrypt_data(user_wrapped_dek, password_key)
        return base64.b64decode(dek_b64)

    @classmethod
    def encrypt_fields(cls, fields: dict[str, Any], dek: bytes) -> str:
        """
        Encrypt multiple fields into a single JSON string.

        Args:
            fields: Dictionary of field_name -> value to encrypt
            dek: Data Encryption Key

        Returns:
            Base64-encoded encrypted JSON
        """
        json_data = json.dumps(fields)
        return cls.encrypt_data(json_data, dek)

    @classmethod
    def decrypt_fields(cls, encrypted_json: str, dek: bytes) -> dict[str, Any]:
        """
        Decrypt fields from encrypted JSON string.

        Args:
            encrypted_json: Base64-encoded encrypted JSON
            dek: Data Encryption Key

        Returns:
            Dictionary of decrypted fields
        """
        json_data = cls.decrypt_data(encrypted_json, dek)
        return json.loads(json_data)

    @classmethod
    def change_password(
        cls, old_password: str, new_password: str, salt: str, user_wrapped_dek: str
    ) -> dict[str, str]:
        """
        Handle password change by re-wrapping the DEK.

        Args:
            old_password: User's current password
            new_password: User's new password
            salt: Base64-encoded salt from PocketBase
            user_wrapped_dek: Current encrypted DEK

        Returns:
            Dictionary with updated encryption data:
            - salt: New salt
            - user_wrapped_dek: DEK re-encrypted with new password
        """
        # Decrypt DEK with old password
        dek = cls.get_user_dek(old_password, salt, user_wrapped_dek)

        # Generate new salt and derive new key
        new_salt = os.urandom(16)
        new_password_key = cls.derive_key_from_password(new_password, new_salt)

        # Re-encrypt DEK with new password-derived key
        new_user_wrapped_dek = cls.encrypt_data(
            base64.b64encode(dek).decode(), new_password_key
        )

        return {
            "salt": base64.b64encode(new_salt).decode(),
            "user_wrapped_dek": new_user_wrapped_dek,
            # Note: admin_wrapped_dek stays the same!
        }


def get_user_data(password: str, user_record: dict[str, Any]) -> dict[str, Any]:
    """
    Retrieve and decrypt user data.

    This would be called when a user logs in or accesses their data.
    """
    # Get DEK using user's password
    dek = EncryptionManager.get_user_dek(
        password, user_record["salt"], user_record["user_wrapped_dek"]
    )

    # Decrypt fields
    decrypted_fields = EncryptionManager.decrypt_fields(
        user_record["encrypted_fields"], dek
    )

    return decrypted_fields


def handle_password_change(
    old_password: str, new_password: str, user_record: dict[str, Any]
) -> dict[str, str]:
    """
    Handle user password change.

    Returns updated encryption data to store in PocketBase.
    """
    updated_data = EncryptionManager.change_password(
        old_password, new_password, user_record["salt"], user_record["user_wrapped_dek"]
    )

    return updated_data
