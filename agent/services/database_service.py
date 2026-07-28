from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_FOLDER = Path("data")
DATABASE_PATH = DATA_FOLDER / "datarakshak.db"


def utc_now() -> str:
    """Return the current UTC date and time."""

    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    """Open the DataRakshak SQLite database."""

    DATA_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """Create the required database tables."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS wipe_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_number TEXT NOT NULL UNIQUE,
                device_name TEXT NOT NULL,
                serial_number TEXT NOT NULL,
                total_bytes INTEGER NOT NULL,
                wipe_method TEXT NOT NULL,
                status TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                certificate_number TEXT,
                error_message TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )

        connection.commit()


def generate_job_number() -> str:
    """Generate a unique wipe-job number."""

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d-%H%M%S")

    random_part = uuid.uuid4().hex[:6].upper()

    return f"JOB-{timestamp}-{random_part}"


def create_wipe_job(
    device_name: str,
    serial_number: str,
    total_bytes: int,
    wipe_method: str,
) -> dict[str, Any]:
    """Create a new pending wipe job."""

    initialize_database()

    job_number = generate_job_number()
    started_at = utc_now()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO wipe_jobs (
                job_number,
                device_name,
                serial_number,
                total_bytes,
                wipe_method,
                status,
                verification_status,
                started_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_number,
                device_name,
                serial_number,
                total_bytes,
                wipe_method,
                "PENDING",
                "NOT_STARTED",
                started_at,
            ),
        )

        connection.commit()

        job_id = cursor.lastrowid

    return get_wipe_job(job_id)


def get_wipe_job(
    job_id: int,
) -> dict[str, Any]:
    """Get one wipe job using its database ID."""

    initialize_database()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM wipe_jobs
            WHERE id = ?
            """,
            (job_id,),
        ).fetchone()

    if row is None:
        raise ValueError(
            f"Wipe job ID {job_id} was not found."
        )

    return dict(row)


def update_wipe_job(
    job_id: int,
    *,
    status: str | None = None,
    verification_status: str | None = None,
    certificate_number: str | None = None,
    error_message: str | None = None,
    mark_completed: bool = False,
) -> dict[str, Any]:
    """Update the status and results of a wipe job."""

    initialize_database()

    updates: list[str] = []
    values: list[Any] = []

    if status is not None:
        updates.append("status = ?")
        values.append(status)

    if verification_status is not None:
        updates.append("verification_status = ?")
        values.append(verification_status)

    if certificate_number is not None:
        updates.append("certificate_number = ?")
        values.append(certificate_number)

    if error_message is not None:
        updates.append("error_message = ?")
        values.append(error_message)

    if mark_completed:
        updates.append("completed_at = ?")
        values.append(utc_now())

    if not updates:
        return get_wipe_job(job_id)

    values.append(job_id)

    with get_connection() as connection:
        cursor = connection.execute(
            f"""
            UPDATE wipe_jobs
            SET {", ".join(updates)}
            WHERE id = ?
            """,
            values,
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"Wipe job ID {job_id} was not found."
            )

        connection.commit()

    return get_wipe_job(job_id)


def list_wipe_jobs(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return the newest wipe jobs."""

    initialize_database()

    safe_limit = max(1, min(limit, 100))

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM wipe_jobs
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


if __name__ == "__main__":
    initialize_database()

    print("Database initialized successfully")
    print("Database path:", DATABASE_PATH)

    test_job = create_wipe_job(
        device_name="Fake Test Disk",
        serial_number="TEST-DISK-0001",
        total_bytes=10 * 1024 * 1024,
        wipe_method="Single-pass zero overwrite",
    )

    print("\nTest job created:")
    print(test_job)

    completed_job = update_wipe_job(
        job_id=test_job["id"],
        status="COMPLETED",
        verification_status="PASSED",
        mark_completed=True,
    )

    print("\nTest job updated:")
    print(completed_job)

    print("\nLatest wipe jobs:")

    for job in list_wipe_jobs(limit=5):
        print(job)