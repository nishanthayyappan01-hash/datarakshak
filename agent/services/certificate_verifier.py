from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from agent.services.signature_service import verify_signature


CERTIFICATES_FOLDER = Path("certificates")


def convert_to_canonical_bytes(
    data: dict[str, Any],
) -> bytes:
    """Convert certificate payload into stable JSON bytes."""

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def find_latest_certificate_json() -> Path:
    """Find the most recently created certificate JSON file."""

    if not CERTIFICATES_FOLDER.exists():
        raise FileNotFoundError(
            "Certificates folder was not found."
        )

    json_files = list(
        CERTIFICATES_FOLDER.glob("DRK-*.json")
    )

    if not json_files:
        raise FileNotFoundError(
            "No certificate JSON records were found."
        )

    return max(
        json_files,
        key=lambda path: path.stat().st_mtime,
    )


def load_certificate_record(
    json_path: Path,
) -> dict[str, Any]:
    """Load and validate the certificate JSON structure."""

    if not json_path.exists():
        raise FileNotFoundError(
            f"Certificate file was not found: {json_path}"
        )

    if not json_path.is_file():
        raise ValueError(
            "Certificate path is not a file."
        )

    if json_path.suffix.lower() != ".json":
        raise ValueError(
            "Only certificate JSON files can be verified."
        )

    try:
        record = json.loads(
            json_path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid certificate JSON: {error}"
        ) from error

    if not isinstance(record, dict):
        raise ValueError(
            "Certificate record must be a JSON object."
        )

    payload = record.get("payload")
    security = record.get("security")

    if not isinstance(payload, dict):
        raise ValueError(
            "Certificate payload is missing or invalid."
        )

    if not isinstance(security, dict):
        raise ValueError(
            "Certificate security section is missing or invalid."
        )

    required_payload_fields = [
        "certificate_number",
        "device_name",
        "serial_number",
        "total_bytes",
        "wipe_method",
        "verification_status",
        "created_at_utc",
    ]

    for field in required_payload_fields:
        if field not in payload:
            raise ValueError(
                f"Certificate payload field missing: {field}"
            )

    required_security_fields = [
        "certificate_hash",
        "digital_signature",
        "hash_algorithm",
        "signature_algorithm",
    ]

    for field in required_security_fields:
        if field not in security:
            raise ValueError(
                f"Certificate security field missing: {field}"
            )

    return record


def verify_certificate(
    json_path: Path,
) -> dict[str, Any]:
    """Verify certificate hash and Ed25519 signature."""

    record = load_certificate_record(
        json_path
    )

    payload = record["payload"]
    security = record["security"]

    payload_bytes = convert_to_canonical_bytes(
        payload
    )

    calculated_hash = hashlib.sha256(
        payload_bytes
    ).hexdigest()

    stored_hash = str(
        security["certificate_hash"]
    )

    hash_valid = (
        calculated_hash == stored_hash
    )

    digital_signature = str(
        security["digital_signature"]
    )

    signature_valid = verify_signature(
        payload_bytes,
        digital_signature,
    )

    algorithm_valid = (
        security["hash_algorithm"] == "SHA-256"
        and security["signature_algorithm"] == "Ed25519"
    )

    certificate_valid = (
        hash_valid
        and signature_valid
        and algorithm_valid
    )

    failed_checks: list[str] = []

    if not hash_valid:
        failed_checks.append(
            "Certificate hash does not match."
        )

    if not signature_valid:
        failed_checks.append(
            "Digital signature is invalid."
        )

    if not algorithm_valid:
        failed_checks.append(
            "Security algorithm information is invalid."
        )

    return {
        "status": (
            "VALID"
            if certificate_valid
            else "TAMPERED"
        ),
        "certificate_number": payload[
            "certificate_number"
        ],
        "device_name": payload[
            "device_name"
        ],
        "serial_number": payload[
            "serial_number"
        ],
        "verification_status": payload[
            "verification_status"
        ],
        "json_path": str(json_path),
        "hash_valid": hash_valid,
        "signature_valid": signature_valid,
        "algorithm_valid": algorithm_valid,
        "stored_hash": stored_hash,
        "calculated_hash": calculated_hash,
        "failed_checks": failed_checks,
    }


def print_verification_result(
    result: dict[str, Any],
) -> None:
    """Print certificate verification details."""

    print("\nDataRakshak Certificate Verification")
    print("-----------------------------------")

    print(
        "Certificate:",
        result["certificate_number"],
    )

    print(
        "Device:",
        result["device_name"],
    )

    print(
        "Serial number:",
        result["serial_number"],
    )

    print(
        "Wipe verification:",
        result["verification_status"],
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
        "Algorithms valid:",
        result["algorithm_valid"],
    )

    print(
        "Final certificate status:",
        result["status"],
    )

    if result["failed_checks"]:
        print("\nFailed checks:")

        for message in result[
            "failed_checks"
        ]:
            print("-", message)


def main() -> None:
    """Verify a selected or latest certificate record."""

    try:
        if len(sys.argv) > 1:
            json_path = Path(
                sys.argv[1]
            )
        else:
            json_path = (
                find_latest_certificate_json()
            )

        print(
            "Verifying certificate:",
            json_path,
        )

        result = verify_certificate(
            json_path
        )

        print_verification_result(
            result
        )

    except Exception as error:
        print(
            "Certificate verification failed:"
        )

        print(error)

        raise SystemExit(1) from error


if __name__ == "__main__":
    main()