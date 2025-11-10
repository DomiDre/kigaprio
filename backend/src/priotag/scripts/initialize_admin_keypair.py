"""Initialize private / public key and secure private key with admin password.
Public key is used on server to encrypt user data encryption keys for admin access
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_admin_keypair():
    # Generate RSA keypair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    # Get admin passphrase for private key encryption
    passphrase = input("Enter passphrase to protect admin private key: ").encode()

    # Serialize private key (encrypted with passphrase)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
    )

    # Serialize public key (no encryption needed)
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Save keys
    with open("admin_private_key.pem", "wb") as f:
        f.write(private_pem)
    print("✓ Private key saved to admin_private_key.pem")
    print("  Store this on admin's laptop/hardware token - NOT on server!")

    with open("admin_public_key.pem", "wb") as f:
        f.write(public_pem)
    print("✓ Public key saved to admin_public_key.pem")
    print("  This goes on the server (safe to store)")


if __name__ == "__main__":
    generate_admin_keypair()
