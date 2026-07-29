from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from agent.paths import (
    PRIVATE_KEY_PATH,
    PUBLIC_KEY_PATH,
    ensure_runtime_directories,
)


SIGNATURE_ALGORITHM = "Ed25519"


class SignatureServiceError(Exception):
    """Raised when a digital-signature operation fails."""


def canonical_json_bytes(
    payload: dict[str, Any],
) -> bytes:
    """Convert a dictionary into deterministic JSON bytes."""

    try:
        canonical_text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    except (TypeError, ValueError) as error:
        raise SignatureServiceError(
            f"Payload cannot be converted to JSON: {error}"
        ) from error

    return canonical_text.encode("utf-8")


def save_private_key(
    private_key: Ed25519PrivateKey,
) -> None:
    """Save the Ed25519 private key in PEM format."""

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    try:
        PRIVATE_KEY_PATH.write_bytes(
            private_key_bytes
        )

    except OSError as error:
        raise SignatureServiceError(
            f"Could not save the private key: {error}"
        ) from error


def save_public_key(
    public_key: Ed25519PublicKey,
) -> None:
    """Save the Ed25519 public key in PEM format."""

    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    try:
        PUBLIC_KEY_PATH.write_bytes(
            public_key_bytes
        )

    except OSError as error:
        raise SignatureServiceError(
            f"Could not save the public key: {error}"
        ) from error


def generate_key_pair() -> dict[str, str]:
    """Generate and save a new Ed25519 signing-key pair."""

    ensure_runtime_directories()

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    save_private_key(private_key)
    save_public_key(public_key)

    return {
        "algorithm": SIGNATURE_ALGORITHM,
        "private_key_path": str(PRIVATE_KEY_PATH),
        "public_key_path": str(PUBLIC_KEY_PATH),
        "public_key_fingerprint": (
            get_public_key_fingerprint(public_key)
        ),
    }


def load_private_key() -> Ed25519PrivateKey:
    """Load the local Ed25519 private key."""

    ensure_runtime_directories()

    if not PRIVATE_KEY_PATH.exists():
        raise SignatureServiceError(
            "The private signing key was not found."
        )

    try:
        key_data = PRIVATE_KEY_PATH.read_bytes()

        loaded_key = serialization.load_pem_private_key(
            key_data,
            password=None,
        )

    except (OSError, ValueError, TypeError) as error:
        raise SignatureServiceError(
            f"Could not load the private key: {error}"
        ) from error

    if not isinstance(
        loaded_key,
        Ed25519PrivateKey,
    ):
        raise SignatureServiceError(
            "The stored private key is not an Ed25519 key."
        )

    return loaded_key


def load_public_key() -> Ed25519PublicKey:
    """Load the local Ed25519 public key."""

    ensure_runtime_directories()

    if not PUBLIC_KEY_PATH.exists():
        raise SignatureServiceError(
            "The public verification key was not found."
        )

    try:
        key_data = PUBLIC_KEY_PATH.read_bytes()

        loaded_key = serialization.load_pem_public_key(
            key_data
        )

    except (OSError, ValueError, TypeError) as error:
        raise SignatureServiceError(
            f"Could not load the public key: {error}"
        ) from error

    if not isinstance(
        loaded_key,
        Ed25519PublicKey,
    ):
        raise SignatureServiceError(
            "The stored public key is not an Ed25519 key."
        )

    return loaded_key


def ensure_signing_keys() -> dict[str, str]:
    """Create signing keys only when both key files are absent."""

    ensure_runtime_directories()

    private_exists = PRIVATE_KEY_PATH.exists()
    public_exists = PUBLIC_KEY_PATH.exists()

    if not private_exists and not public_exists:
        return generate_key_pair()

    if private_exists and not public_exists:
        private_key = load_private_key()
        public_key = private_key.public_key()

        save_public_key(public_key)

    elif public_exists and not private_exists:
        raise SignatureServiceError(
            "The public key exists, but the private key is missing. "
            "Certificate signing has been blocked to prevent "
            "an accidental key replacement."
        )

    public_key = load_public_key()

    return {
        "algorithm": SIGNATURE_ALGORITHM,
        "private_key_path": str(PRIVATE_KEY_PATH),
        "public_key_path": str(PUBLIC_KEY_PATH),
        "public_key_fingerprint": (
            get_public_key_fingerprint(public_key)
        ),
    }


def get_public_key_fingerprint(
    public_key: Ed25519PublicKey | None = None,
) -> str:
    """Return the SHA-256 fingerprint of the public key."""

    active_public_key = (
        public_key
        if public_key is not None
        else load_public_key()
    )

    public_key_bytes = active_public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return hashlib.sha256(
        public_key_bytes
    ).hexdigest()


def sign_payload(
    payload: dict[str, Any],
) -> dict[str, str]:
    """Digitally sign a canonical JSON payload."""

    ensure_signing_keys()

    private_key = load_private_key()
    payload_bytes = canonical_json_bytes(payload)

    try:
        signature_bytes = private_key.sign(
            payload_bytes
        )

    except Exception as error:
        raise SignatureServiceError(
            f"Could not sign the certificate payload: {error}"
        ) from error

    signature_base64 = base64.b64encode(
        signature_bytes
    ).decode("ascii")

    return {
        "algorithm": SIGNATURE_ALGORITHM,
        "signature": signature_base64,
        "public_key_fingerprint": (
            get_public_key_fingerprint()
        ),
    }


def verify_payload_signature(
    payload: dict[str, Any],
    signature_base64: str,
) -> bool:
    """Verify an Ed25519 signature using the local public key."""

    if not signature_base64.strip():
        return False

    try:
        signature_bytes = base64.b64decode(
            signature_base64,
            validate=True,
        )

        public_key = load_public_key()

        public_key.verify(
            signature_bytes,
            canonical_json_bytes(payload),
        )

        return True

    except (
        InvalidSignature,
        ValueError,
        TypeError,
        SignatureServiceError,
    ):
        return False


def main() -> None:
    """Prepare signing keys and display safe key information."""

    key_information = ensure_signing_keys()

    print(
        "Signature algorithm:",
        key_information["algorithm"],
    )

    print(
        "Private key path:",
        key_information["private_key_path"],
    )

    print(
        "Public key path:",
        key_information["public_key_path"],
    )

    print(
        "Public-key fingerprint:",
        key_information["public_key_fingerprint"],
    )


if __name__ == "__main__":
    main()