from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_FOLDER = Path("audit_logs")
AUDIT_FILE = AUDIT_FOLDER / "audit_log.jsonl"


def calculate_hash(data: dict[str, Any]) -> str:
    """Generate a SHA-256 hash for an audit-log entry."""

    canonical_data = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(canonical_data).hexdigest()


def get_previous_hash() -> str:
    """Read the hash of the latest audit-log entry."""

    if not AUDIT_FILE.exists():
        return "GENESIS"

    lines = AUDIT_FILE.read_text(
        encoding="utf-8"
    ).splitlines()

    if not lines:
        return "GENESIS"

    latest_entry = json.loads(lines[-1])

    return latest_entry["current_hash"]


def write_audit_log(
    action: str,
    status: str,
    details: dict[str, Any] | None = None,
    user: str = "Local Technician",
) -> dict[str, Any]:
    """Create a tamper-evident audit-log entry."""

    AUDIT_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    previous_hash = get_previous_hash()

    entry_data = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "user": user,
        "action": action,
        "status": status,
        "details": details or {},
        "previous_hash": previous_hash,
    }

    current_hash = calculate_hash(entry_data)

    complete_entry = {
        **entry_data,
        "current_hash": current_hash,
    }

    with AUDIT_FILE.open(
        "a",
        encoding="utf-8",
    ) as log_file:
        log_file.write(
            json.dumps(
                complete_entry,
                sort_keys=True,
            )
            + "\n"
        )

    return complete_entry


def verify_audit_log() -> dict[str, Any]:
    """Verify that the audit-log hash chain was not modified."""

    if not AUDIT_FILE.exists():
        return {
            "status": "empty",
            "entries_checked": 0,
            "message": "Audit log does not exist.",
        }

    lines = AUDIT_FILE.read_text(
        encoding="utf-8"
    ).splitlines()

    expected_previous_hash = "GENESIS"

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        entry = json.loads(line)

        stored_current_hash = entry.pop(
            "current_hash"
        )

        if entry["previous_hash"] != expected_previous_hash:
            return {
                "status": "failed",
                "entries_checked": line_number - 1,
                "failed_line": line_number,
                "message": "Previous hash does not match.",
            }

        calculated_hash = calculate_hash(entry)

        if calculated_hash != stored_current_hash:
            return {
                "status": "failed",
                "entries_checked": line_number - 1,
                "failed_line": line_number,
                "message": "Audit entry was modified.",
            }

        expected_previous_hash = stored_current_hash

    return {
        "status": "passed",
        "entries_checked": len(lines),
        "message": "Audit log hash chain is valid.",
    }


if __name__ == "__main__":
    created_entry = write_audit_log(
        action="AUDIT_LOG_TEST",
        status="SUCCESS",
        details={
            "message": "DataRakshak audit logger test",
        },
    )

    print("Audit entry created successfully")
    print("Current hash:", created_entry["current_hash"])

    verification_result = verify_audit_log()

    print("Verification result:", verification_result)