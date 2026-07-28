from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from agent.paths import (
    DATABASE_PATH,
    ensure_runtime_directories,
)


class DatabaseError(Exception):
    """Raised when a DataRakshak database operation fails."""


def current_timestamp() -> str:
    """Return the current UTC timestamp."""

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def create_job_number() -> str:
    """Create a unique wipe-job number."""

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d-%H%M%S")

    unique_part = uuid.uuid4().hex[:8].upper()

    return f"DRK-JOB-{timestamp}-{unique_part}"


def connect_database() -> sqlite3.Connection:
    """Open the DataRakshak SQLite database."""

    ensure_runtime_directories()

    try:
        connection = sqlite3.connect(
            DATABASE_PATH,
            timeout=15,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        return connection

    except sqlite3.Error as error:
        raise DatabaseError(
            f"Could not open the database: {error}"
        ) from error


def get_existing_columns(
    connection: sqlite3.Connection,
) -> set[str]:
    """Return the existing wipe_jobs column names."""

    rows = connection.execute(
        "PRAGMA table_info(wipe_jobs)"
    ).fetchall()

    return {
        str(row["name"])
        for row in rows
    }


def migrate_database(
    connection: sqlite3.Connection,
) -> None:
    """Upgrade older database schemas without deleting history."""

    existing_columns = get_existing_columns(
        connection
    )

    required_columns = {
        "job_number": "TEXT",
        "device_name": "TEXT",
        "serial_number": "TEXT",
        "total_bytes": "INTEGER DEFAULT 0",
        "wipe_method": "TEXT",
        "status": "TEXT DEFAULT 'CREATED'",
        "verification_status": (
            "TEXT DEFAULT 'PENDING'"
        ),
        "certificate_number": "TEXT",
        "error_message": "TEXT",
        "started_at": "TEXT",
        "updated_at": "TEXT",
        "completed_at": "TEXT",
    }

    for column_name, column_definition in (
        required_columns.items()
    ):
        if column_name in existing_columns:
            continue

        connection.execute(
            (
                "ALTER TABLE wipe_jobs "
                f"ADD COLUMN {column_name} "
                f"{column_definition}"
            )
        )

    timestamp = current_timestamp()

    connection.execute(
        """
        UPDATE wipe_jobs
        SET status = 'CREATED'
        WHERE status IS NULL
           OR TRIM(status) = ''
        """
    )

    connection.execute(
        """
        UPDATE wipe_jobs
        SET verification_status = 'PENDING'
        WHERE verification_status IS NULL
           OR TRIM(verification_status) = ''
        """
    )

    connection.execute(
        """
        UPDATE wipe_jobs
        SET device_name = 'Legacy Device'
        WHERE device_name IS NULL
           OR TRIM(device_name) = ''
        """
    )

    connection.execute(
        """
        UPDATE wipe_jobs
        SET serial_number = 'UNKNOWN'
        WHERE serial_number IS NULL
           OR TRIM(serial_number) = ''
        """
    )

    connection.execute(
        """
        UPDATE wipe_jobs
        SET wipe_method = 'Legacy wipe method'
        WHERE wipe_method IS NULL
           OR TRIM(wipe_method) = ''
        """
    )

    connection.execute(
        """
        UPDATE wipe_jobs
        SET total_bytes = 0
        WHERE total_bytes IS NULL
        """
    )

    connection.execute(
        """
        UPDATE wipe_jobs
        SET started_at = ?
        WHERE started_at IS NULL
           OR TRIM(started_at) = ''
        """,
        (timestamp,),
    )

    connection.execute(
        """
        UPDATE wipe_jobs
        SET updated_at = COALESCE(
            NULLIF(updated_at, ''),
            started_at,
            ?
        )
        """,
        (timestamp,),
    )

    legacy_rows = connection.execute(
        """
        SELECT id
        FROM wipe_jobs
        WHERE job_number IS NULL
           OR TRIM(job_number) = ''
        """
    ).fetchall()

    for row in legacy_rows:
        job_id = int(row["id"])

        legacy_job_number = (
            f"DRK-LEGACY-{job_id}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        connection.execute(
            """
            UPDATE wipe_jobs
            SET job_number = ?
            WHERE id = ?
            """,
            (
                legacy_job_number,
                job_id,
            ),
        )


def initialize_database() -> None:
    """Create or upgrade the wipe-jobs database."""

    create_table_query = """
        CREATE TABLE IF NOT EXISTS wipe_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_number TEXT NOT NULL UNIQUE,
            device_name TEXT NOT NULL,
            serial_number TEXT NOT NULL,
            total_bytes INTEGER NOT NULL,
            wipe_method TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'CREATED',
            verification_status TEXT NOT NULL DEFAULT 'PENDING',
            certificate_number TEXT,
            error_message TEXT,
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        )
    """

    create_job_number_index = """
        CREATE INDEX IF NOT EXISTS
        idx_wipe_jobs_job_number
        ON wipe_jobs(job_number)
    """

    create_status_index = """
        CREATE INDEX IF NOT EXISTS
        idx_wipe_jobs_status
        ON wipe_jobs(status)
    """

    try:
        with connect_database() as connection:
            connection.execute(
                create_table_query
            )

            migrate_database(
                connection
            )

            connection.execute(
                create_job_number_index
            )

            connection.execute(
                create_status_index
            )

            connection.commit()

    except sqlite3.Error as error:
        raise DatabaseError(
            f"Could not initialise the database: {error}"
        ) from error


def row_to_dictionary(
    row: sqlite3.Row | None,
) -> dict[str, Any] | None:
    """Convert a SQLite row into a dictionary."""

    if row is None:
        return None

    return dict(row)


def get_wipe_job(
    job_id: int,
) -> dict[str, Any] | None:
    """Return one wipe job using its database ID."""

    initialize_database()

    try:
        with connect_database() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    job_number,
                    device_name,
                    serial_number,
                    total_bytes,
                    wipe_method,
                    status,
                    verification_status,
                    certificate_number,
                    error_message,
                    started_at,
                    updated_at,
                    completed_at
                FROM wipe_jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()

        return row_to_dictionary(row)

    except sqlite3.Error as error:
        raise DatabaseError(
            f"Could not read wipe job {job_id}: {error}"
        ) from error


def create_wipe_job(
    device_name: str,
    serial_number: str,
    total_bytes: int,
    wipe_method: str,
) -> dict[str, Any]:
    """Create and return a new wipe job."""

    initialize_database()

    if not device_name.strip():
        raise DatabaseError(
            "Device name cannot be empty."
        )

    if not serial_number.strip():
        raise DatabaseError(
            "Serial number cannot be empty."
        )

    if total_bytes <= 0:
        raise DatabaseError(
            "Total bytes must be greater than zero."
        )

    if not wipe_method.strip():
        raise DatabaseError(
            "Wipe method cannot be empty."
        )

    job_number = create_job_number()
    timestamp = current_timestamp()

    try:
        with connect_database() as connection:
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
                    started_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_number,
                    device_name.strip(),
                    serial_number.strip(),
                    total_bytes,
                    wipe_method.strip(),
                    "CREATED",
                    "PENDING",
                    timestamp,
                    timestamp,
                ),
            )

            connection.commit()

            job_id = cursor.lastrowid

        if job_id is None:
            raise DatabaseError(
                "The database did not return a job ID."
            )

        created_job = get_wipe_job(
            int(job_id)
        )

        if created_job is None:
            raise DatabaseError(
                "The created wipe job could not be loaded."
            )

        return created_job

    except sqlite3.IntegrityError as error:
        raise DatabaseError(
            f"Could not create a unique wipe job: {error}"
        ) from error

    except sqlite3.Error as error:
        raise DatabaseError(
            f"Could not create the wipe job: {error}"
        ) from error


def update_wipe_job(
    job_id: int,
    status: str | None = None,
    verification_status: str | None = None,
    certificate_number: str | None = None,
    error_message: str | None = None,
    mark_completed: bool = False,
) -> dict[str, Any]:
    """Update selected fields of a wipe job."""

    initialize_database()

    updates: list[str] = []
    values: list[Any] = []

    if status is not None:
        updates.append("status = ?")
        values.append(status)

    if verification_status is not None:
        updates.append(
            "verification_status = ?"
        )
        values.append(verification_status)

    if certificate_number is not None:
        updates.append(
            "certificate_number = ?"
        )
        values.append(certificate_number)

    if error_message is not None:
        updates.append(
            "error_message = ?"
        )
        values.append(error_message)

    timestamp = current_timestamp()

    updates.append("updated_at = ?")
    values.append(timestamp)

    if mark_completed:
        updates.append("completed_at = ?")
        values.append(timestamp)

    values.append(job_id)

    update_query = f"""
        UPDATE wipe_jobs
        SET {", ".join(updates)}
        WHERE id = ?
    """

    try:
        with connect_database() as connection:
            cursor = connection.execute(
                update_query,
                values,
            )

            connection.commit()

            if cursor.rowcount == 0:
                raise DatabaseError(
                    f"Wipe job {job_id} was not found."
                )

        updated_job = get_wipe_job(job_id)

        if updated_job is None:
            raise DatabaseError(
                "The updated wipe job could not be loaded."
            )

        return updated_job

    except sqlite3.Error as error:
        raise DatabaseError(
            f"Could not update wipe job {job_id}: {error}"
        ) from error


def list_wipe_jobs(
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return recent wipe jobs, newest first."""

    initialize_database()

    safe_limit = max(
        1,
        min(limit, 500),
    )

    try:
        with connect_database() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    job_number,
                    device_name,
                    serial_number,
                    total_bytes,
                    wipe_method,
                    status,
                    verification_status,
                    certificate_number,
                    error_message,
                    started_at,
                    updated_at,
                    completed_at
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

    except sqlite3.Error as error:
        raise DatabaseError(
            f"Could not load wipe history: {error}"
        ) from error


if __name__ == "__main__":
    initialize_database()

    print(
        "DataRakshak database initialised successfully."
    )

    print(
        "Database path:",
        DATABASE_PATH,
    )

    jobs = list_wipe_jobs(limit=5)

    print(
        "Recent wipe jobs:",
        len(jobs),
    )