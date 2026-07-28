from __future__ import annotations

import base64
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


KEYS_FOLDER = Path("keys")
PRIVATE_KEY_PATH = KEYS_FOLDER / "private_key.pem"
PUBLIC_KEY_PATH = KEYS_FOLDER / "public_key.pem"


def generate_key_pair() -> dict[str, str]:
    """Generate an Ed25519 private and public key pair."""

    KEYS_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        PRIVATE_KEY_PATH.exists()
        and PUBLIC_KEY_PATH.exists()
    ):
        return {
            "status": "already_exists",
            "private_key_path": str(PRIVATE_KEY_PATH),
            "public_key_path": str(PUBLIC_KEY_PATH),
        }

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    PRIVATE_KEY_PATH.write_bytes(
        private_key_bytes
    )

    PUBLIC_KEY_PATH.write_bytes(
        public_key_bytes
    )

    return {
        "status": "created",
        "private_key_path": str(PRIVATE_KEY_PATH),
        "public_key_path": str(PUBLIC_KEY_PATH),
    }


def load_private_key() -> Ed25519PrivateKey:
    """Load the local Ed25519 private key."""

    if not PRIVATE_KEY_PATH.exists():
        generate_key_pair()

    private_key_data = PRIVATE_KEY_PATH.read_bytes()

    private_key = serialization.load_pem_private_key(
        private_key_data,
        password=None,
    )

    if not isinstance(
        private_key,
        Ed25519PrivateKey,
    ):
        raise TypeError(
            "The stored private key is not an Ed25519 key."
        )

    return private_key


def load_public_key() -> Ed25519PublicKey:
    """Load the local Ed25519 public key."""

    if not PUBLIC_KEY_PATH.exists():
        generate_key_pair()

    public_key_data = PUBLIC_KEY_PATH.read_bytes()

    public_key = serialization.load_pem_public_key(
        public_key_data
    )

    if not isinstance(
        public_key,
        Ed25519PublicKey,
    ):
        raise TypeError(
            "The stored public key is not an Ed25519 key."
        )

    return public_key


def sign_data(data: bytes) -> str:
    """Digitally sign bytes and return a Base64 signature."""

    if not isinstance(data, bytes):
        raise TypeError(
            "Data supplied for signing must be bytes."
        )

    private_key = load_private_key()

    signature = private_key.sign(data)

    return base64.b64encode(
        signature
    ).decode("utf-8")


def verify_signature(
    data: bytes,
    signature_base64: str,
) -> bool:
    """Verify a Base64 Ed25519 digital signature."""

    if not isinstance(data, bytes):
        raise TypeError(
            "Data supplied for verification must be bytes."
        )

    public_key = load_public_key()

    try:
        signature = base64.b64decode(
            signature_base64,
            validate=True,
        )

        public_key.verify(
            signature,
            data,
        )

        return True

    except (
        InvalidSignature,
        ValueError,
        TypeError,
    ):
        return False


if __name__ == "__main__":
    key_result = generate_key_pair()

    print("Key status:", key_result["status"])
    print(
        "Private key:",
        key_result["private_key_path"],
    )
    print(
        "Public key:",
        key_result["public_key_path"],
    )

    original_data = (
        b"DataRakshak certificate test data"
    )

    digital_signature = sign_data(
        original_data
    )

    print("\nDigital signature created:")
    print(digital_signature)

    original_result = verify_signature(
        original_data,
        digital_signature,
    )

    print(
        "\nOriginal data verification:",
        original_result,
    )

    modified_data = (
        b"DataRakshak certificate MODIFIED data"
    )

    modified_result = verify_signature(
        modified_data,
        digital_signature,
    )

    print(
        "Modified data verification:",
        modified_result,
    )