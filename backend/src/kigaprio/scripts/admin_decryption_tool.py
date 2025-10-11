"""
Admin tool for decrypting user data.
Runs on admin's laptop - NOT on the server!
"""

import argparse
import base64
import json
import os
from getpass import getpass
from pathlib import Path
from typing import Any

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey  # Specific type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AdminDecryptor:
    """Client-side admin decryption tool."""

    def __init__(self, private_key_path: str, api_url: str, admin_token: str):
        self.api_url = api_url
        self.admin_token = admin_token
        self.private_key = self._load_private_key(private_key_path)

    def _load_private_key(self, key_path: str) -> RSAPrivateKey:
        """Load admin's RSA private key (prompts for passphrase)."""
        passphrase = getpass("Enter admin private key passphrase: ").encode()

        private_key_pem = Path(key_path).expanduser().read_bytes()
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=passphrase, backend=default_backend()
        )

        # Type check
        if not isinstance(private_key, RSAPrivateKey):
            raise TypeError(f"Expected RSA private key, got {type(private_key)}")

        return private_key

    def get_admin_dek(self, admin_wrapped_dek: str) -> bytes:
        """
        Unwrap user's DEK using admin's PRIVATE key.
        Equivalent to server's get_user_dek, but for admin.
        """
        encrypted_dek = base64.b64decode(admin_wrapped_dek)

        # Decrypt with RSA private key
        dek = self.private_key.decrypt(
            encrypted_dek,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return dek

    def decrypt_fields(self, encrypted_json: str, dek: bytes) -> dict[str, Any]:
        """Decrypt user fields using DEK."""
        encrypted = base64.b64decode(encrypted_json)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]

        aesgcm = AESGCM(dek)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        return json.loads(plaintext.decode())

    def fetch_and_decrypt_user(self, user_id: str) -> dict:
        """
        Complete flow: fetch encrypted data, unwrap DEK, decrypt fields.
        """
        # 1. Fetch encrypted data from server
        response = requests.get(
            f"{self.api_url}/api/v1/admin/users/info/{user_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        response.raise_for_status()
        user_data = response.json()

        # 2. Unwrap DEK using admin's private key
        dek = self.get_admin_dek(user_data["admin_wrapped_dek"])

        # 3. Decrypt user fields using DEK
        decrypted_fields = self.decrypt_fields(user_data["encrypted_fields"], dek)

        return {
            "username": user_data["username"],
            "created": user_data.get("created"),
            **decrypted_fields,  # fullName, etc.
        }


def main():
    parser = argparse.ArgumentParser(
        description="Admin tool to decrypt user data using RSA private key",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s user123
  %(prog)s user123 --api-url https://api.example.com
  %(prog)s user123 --key-path /path/to/key.pem --token mytoken123

Environment Variables:
  API_URL       Backend API URL (default: http://localhost:8000)
  ADMIN_TOKEN   Admin JWT authentication token (required if not passed via --token)
        """,
    )

    # Positional arguments
    parser.add_argument("user_id", help="User ID to decrypt data for")

    # Optional arguments
    parser.add_argument(
        "--api-url",
        default=os.getenv("API_URL", "http://localhost:8000"),
        help="Backend API URL (default: %(default)s or $API_URL)",
    )

    parser.add_argument(
        "--token",
        default=os.getenv("ADMIN_TOKEN"),
        help="Admin JWT token (default: $ADMIN_TOKEN)",
    )

    parser.add_argument(
        "--key-path",
        default="~/secure_keys/admin_private_key.pem",
        help="Path to admin RSA private key (default: %(default)s)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Validate required arguments
    if not args.token:
        parser.error(
            "ADMIN_TOKEN is required. Set via --token or $ADMIN_TOKEN environment variable"
        )

    if args.verbose:
        print(f"API URL: {args.api_url}")
        print(f"Key path: {args.key_path}")
        print(f"User ID: {args.user_id}")
        print()

    try:
        decryptor = AdminDecryptor(
            private_key_path=args.key_path,
            api_url=args.api_url,
            admin_token=args.token,
        )

        if args.verbose:
            print(f"Fetching and decrypting user {args.user_id}...")

        decrypted_data = decryptor.fetch_and_decrypt_user(args.user_id)

        print("\n✓ Decrypted user data:")
        print(json.dumps(decrypted_data, indent=2))

    except FileNotFoundError as e:
        print(f"✗ Error: Private key file not found: {e}")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"✗ API Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
