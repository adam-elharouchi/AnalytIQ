"""
Generate RSA key pair for LTI 1.3 tool signing.

Run once per deployment. Copy the output into your .env file as:
  LTI_PRIVATE_KEY=<private key with \\n escaping newlines>
  LTI_PUBLIC_KEY=<public key with \\n escaping newlines>

Usage:
  python3 scripts/generate_lti_keys.py
"""

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rsa_keypair(key_size: int = 2048):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    return private_pem, public_pem


if __name__ == "__main__":
    private_pem, public_pem = generate_rsa_keypair()

    # Single-line versions for .env files (newlines replaced with \n literal)
    private_env = private_pem.replace("\n", "\\n")
    public_env = public_pem.replace("\n", "\\n")

    print("# ---------------------------------------------------------------")
    print("# Paste these into your .env file (or Render / Heroku env vars)")
    print("# ---------------------------------------------------------------")
    print()
    print(f"LTI_PRIVATE_KEY={private_env}")
    print()
    print(f"LTI_PUBLIC_KEY={public_env}")
    print()
    print("# ---------------------------------------------------------------")
    print("# Raw PEM (for reference / manual copy)")
    print("# ---------------------------------------------------------------")
    print()
    print("=== PRIVATE KEY (keep secret) ===")
    print(private_pem)
    print("=== PUBLIC KEY (share with LMS platforms) ===")
    print(public_pem)
