from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from agent.paths import (
    AUDIT_LOG_PATH,
    ensure_runtime_directories,
)


GENESIS_HASH = "0" * 64


class AuditLogError(Exception):
    """Raised when an audit-log operation fails."""


def current_timestamp() -> str:
    """Return the current UTC timestamp."""

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def canonical_json(
    value: dict[str, Any],
) -> str:
    """Return deterministic JSON for hash calculation."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def calculate_entry_hash(
    entry_without_hash: dict[str, Any],
) -> str:
    """Calculate the SHA-256 hash of one audit entry."""

    encoded_entry = canonical_json(
        entry_without_hash
    ).encode("utf-8")

    return hashlib.sha256(
        encoded_entry
    ).hexdigest()


def read_audit_entries() -> list[dict[str, Any]]:
    """Read all non-empty audit-log entries."""

    ensure_runtime_directories()

    if not AUDIT_LOG_PATH.exists():
        return []

    try:
        lines = AUDIT_LOG_PATH.read_text(
            encoding="utf-8"
        ).splitlines()

    except OSError as error:
        raise AuditLogError(
            f"Could not read the audit log: {error}"
        ) from error

    entries: list[dict[str, Any]] = []

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        if not line.strip():
            continue

        try:
            entry = json.loads(line)

        except json.JSONDecodeError as error:
            raise AuditLogError(
                "Invalid JSON was found in the audit log "
                f"at line {line_number}."
            ) from error

        if not isinstance(entry, dict):
            raise AuditLogError(
                "Invalid audit entry format "
                f"at line {line_number}."
            )

        entries.append(entry)

    return entries


def verify_audit_log() -> dict[str, Any]:
    """Verify the complete audit-log hash chain."""

    try:
        entries = read_audit_entries()

    except AuditLogError as error:
        return {
            "status": "failed",
            "entries_checked": 0,
            "message": str(error),
        }

    if not entries:
        return {
            "status": "empty",
            "entries_checked": 0,
            "message": "The audit log is empty.",
        }

    expected_previous_hash = GENESIS_HASH
    entries_checked = 0

    required_fields = {
        "timestamp",
        "action",
        "status",
        "details",
        "previous_hash",
        "entry_hash",
    }

    for line_number, entry in enumerate(
        entries,
        start=1,
    ):
        missing_fields = (
            required_fields - set(entry.keys())
        )

        if missing_fields:
            missing_text = ", ".join(
                sorted(missing_fields)
            )

            return {
                "status": "failed",
                "entries_checked": entries_checked,
                "failed_line": line_number,
                "message": (
                    "Audit entry is missing required fields "
                    f"at line {line_number}: {missing_text}"
                ),
            }

        stored_previous_hash = str(
            entry.get("previous_hash")
        )

        if stored_previous_hash != expected_previous_hash:
            return {
                "status": "failed",
                "entries_checked": entries_checked,
                "failed_line": line_number,
                "message": (
                    "Previous-hash mismatch was found "
                    f"at line {line_number}."
                ),
            }

        stored_entry_hash = str(
            entry.get("entry_hash")
        )

        entry_without_hash = {
            key: value
            for key, value in entry.items()
            if key != "entry_hash"
        }

        calculated_hash = calculate_entry_hash(
            entry_without_hash
        )

        if stored_entry_hash != calculated_hash:
            return {
                "status": "failed",
                "entries_checked": entries_checked,
                "failed_line": line_number,
                "message": (
                    "Audit-entry hash mismatch was found "
                    f"at line {line_number}."
                ),
            }

        expected_previous_hash = (
            stored_entry_hash
        )

        entries_checked += 1

    return {
        "status": "passed",
        "entries_checked": entries_checked,
        "message": (
            "The complete audit-log hash chain is valid."
        ),
        "final_hash": expected_previous_hash,
    }


def get_latest_entry_hash() -> str:
    """Return the final valid audit-entry hash."""

    verification = verify_audit_log()

    if verification["status"] == "empty":
        return GENESIS_HASH

    if verification["status"] != "passed":
        raise AuditLogError(
            "New audit data cannot be written because "
            f"the existing log is invalid: "
            f"{verification['message']}"
        )

    return str(
        verification["final_hash"]
    )


def write_audit_log(
    action: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one tamper-evident entry to the audit log."""

    ensure_runtime_directories()

    clean_action = action.strip()
    clean_status = status.strip()

    if not clean_action:
        raise AuditLogError(
            "Audit action cannot be empty."
        )

    if not clean_status:
        raise AuditLogError(
            "Audit status cannot be empty."
        )

    previous_hash = get_latest_entry_hash()

    entry_without_hash: dict[str, Any] = {
        "timestamp": current_timestamp(),
        "action": clean_action,
        "status": clean_status,
        "details": details or {},
        "previous_hash": previous_hash,
    }

    entry_hash = calculate_entry_hash(
        entry_without_hash
    )

    complete_entry = {
        **entry_without_hash,
        "entry_hash": entry_hash,
    }

    serialized_entry = canonical_json(
        complete_entry
    )

    try:
        with AUDIT_LOG_PATH.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as audit_file:
            audit_file.write(
                serialized_entry + "\n"
            )

            audit_file.flush()
            os.fsync(
                audit_file.fileno()
            )

    except OSError as error:
        raise AuditLogError(
            f"Could not write the audit log: {error}"
        ) from error

    return {
        "status": "written",
        "path": str(AUDIT_LOG_PATH),
        "entry_hash": entry_hash,
        "previous_hash": previous_hash,
        "entry": complete_entry,
    }


def main() -> None:
    """Display the current audit-log verification result."""

    result = verify_audit_log()

    print(
        "Audit log path:",
        AUDIT_LOG_PATH,
    )

    print(
        "Verification status:",
        result["status"],
    )

    print(
        "Entries checked:",
        result["entries_checked"],
    )

    print(
        "Message:",
        result["message"],
    )


if __name__ == "__main__":
    main()