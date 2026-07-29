from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from agent.paths import (
    CERTIFICATES_DIR,
    ensure_runtime_directories,
)
from agent.services.signature_service import (
    SIGNATURE_ALGORITHM,
    canonical_json_bytes,
    get_public_key_fingerprint,
    verify_payload_signature,
)


class CertificateVerificationError(Exception):
    """Raised when a certificate cannot be verified."""


def calculate_payload_hash(
    payload: dict[str, Any],
) -> str:
    """Calculate the SHA-256 hash of a certificate payload."""

    return hashlib.sha256(
        canonical_json_bytes(payload)
    ).hexdigest()


def load_certificate_document(
    certificate_path: Path | str,
) -> tuple[Path, dict[str, Any]]:
    """Load and validate a certificate JSON document."""

    ensure_runtime_directories()

    resolved_path = Path(
        certificate_path
    ).expanduser().resolve()

    if not resolved_path.exists():
        raise CertificateVerificationError(
            "The selected certificate file was not found."
        )

    if not resolved_path.is_file():
        raise CertificateVerificationError(
            "The selected certificate path is not a file."
        )

    if resolved_path.suffix.lower() != ".json":
        raise CertificateVerificationError(
            "Only DataRakshak JSON certificate files are supported."
        )

    try:
        certificate_text = resolved_path.read_text(
            encoding="utf-8-sig"
        )

    except OSError as error:
        raise CertificateVerificationError(
            f"Could not read the certificate file: {error}"
        ) from error

    try:
        certificate_document = json.loads(
            certificate_text
        )

    except json.JSONDecodeError as error:
        raise CertificateVerificationError(
            "The selected certificate contains invalid JSON."
        ) from error

    if not isinstance(
        certificate_document,
        dict,
    ):
        raise CertificateVerificationError(
            "The certificate document has an invalid format."
        )

    return (
        resolved_path,
        certificate_document,
    )


def verify_certificate(
    certificate_path: Path | str,
) -> dict[str, Any]:
    """Verify certificate hash, signature and key fingerprint."""

    resolved_path, certificate_document = (
        load_certificate_document(
            certificate_path
        )
    )

    payload = certificate_document.get(
        "payload"
    )

    if not isinstance(payload, dict):
        raise CertificateVerificationError(
            "The certificate payload is missing or invalid."
        )

    certificate_number = str(
        payload.get(
            "certificate_number",
            "UNKNOWN",
        )
    )

    device_name = str(
        payload.get(
            "device_name",
            "Unknown Device",
        )
    )

    stored_hash = str(
        certificate_document.get(
            "certificate_hash",
            "",
        )
    ).strip()

    calculated_hash = calculate_payload_hash(
        payload
    )

    hash_valid = bool(
        stored_hash
    ) and hmac.compare_digest(
        stored_hash,
        calculated_hash,
    )

    digital_signature = (
        certificate_document.get(
            "digital_signature"
        )
    )

    if not isinstance(
        digital_signature,
        dict,
    ):
        digital_signature = {}

    stored_algorithm = str(
        digital_signature.get(
            "algorithm",
            "",
        )
    ).strip()

    signature_value = str(
        digital_signature.get(
            "signature",
            "",
        )
    ).strip()

    stored_fingerprint = str(
        digital_signature.get(
            "public_key_fingerprint",
            "",
        )
    ).strip()

    algorithm_valid = (
        stored_algorithm
        == SIGNATURE_ALGORITHM
    )

    signature_valid = False

    if algorithm_valid and signature_value:
        signature_valid = (
            verify_payload_signature(
                payload=payload,
                signature_base64=signature_value,
            )
        )

    current_fingerprint = ""

    try:
        current_fingerprint = (
            get_public_key_fingerprint()
        )

        fingerprint_valid = bool(
            stored_fingerprint
        ) and hmac.compare_digest(
            stored_fingerprint,
            current_fingerprint,
        )

    except Exception:
        fingerprint_valid = False

    failed_checks: list[str] = []

    if not hash_valid:
        failed_checks.append(
            "Certificate hash mismatch."
        )

    if not algorithm_valid:
        failed_checks.append(
            "Unsupported digital-signature algorithm."
        )

    if not signature_valid:
        failed_checks.append(
            "Digital signature is invalid."
        )

    if not fingerprint_valid:
        failed_checks.append(
            "Public-key fingerprint mismatch."
        )

    all_checks_valid = (
        hash_valid
        and algorithm_valid
        and signature_valid
        and fingerprint_valid
    )

    status = (
        "VALID"
        if all_checks_valid
        else "TAMPERED"
    )

    return {
        "status": status,
        "certificate_number": certificate_number,
        "device_name": device_name,
        "json_path": str(resolved_path),
        "schema_version": certificate_document.get(
            "schema_version",
            "UNKNOWN",
        ),
        "hash_valid": hash_valid,
        "signature_valid": signature_valid,
        "algorithm_valid": algorithm_valid,
        "fingerprint_valid": fingerprint_valid,
        "stored_hash": stored_hash,
        "calculated_hash": calculated_hash,
        "stored_fingerprint": stored_fingerprint,
        "current_fingerprint": current_fingerprint,
        "failed_checks": failed_checks,
    }


def find_latest_certificate() -> Path | None:
    """Return the latest normal certificate JSON file."""

    ensure_runtime_directories()

    certificate_files = [
        path
        for path in CERTIFICATES_DIR.glob(
            "DRK-*.json"
        )
        if "_tampered" not in path.stem.lower()
    ]

    if not certificate_files:
        return None

    return max(
        certificate_files,
        key=lambda path: path.stat().st_mtime,
    )


def main() -> None:
    """Verify the latest local certificate."""

    latest_certificate = (
        find_latest_certificate()
    )

    if latest_certificate is None:
        print(
            "No DataRakshak JSON certificate was found."
        )
        return

    try:
        result = verify_certificate(
            latest_certificate
        )

    except CertificateVerificationError as error:
        print(
            "Certificate verification failed:"
        )
        print(error)
        raise SystemExit(1) from error

    print(
        "Certificate path:",
        result["json_path"],
    )

    print(
        "Certificate number:",
        result["certificate_number"],
    )

    print(
        "Verification status:",
        result["status"],
    )

    print(
        "Hash valid:",
        result["hash_valid"],
    )

    print(
        "Digital signature valid:",
        result["signature_valid"],
    )

    print(
        "Public-key fingerprint valid:",
        result["fingerprint_valid"],
    )

    if result["failed_checks"]:
        print(
            "Failed checks:",
            ", ".join(
                result["failed_checks"]
            ),
        )


if __name__ == "__main__":
    main()