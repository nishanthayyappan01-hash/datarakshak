from __future__ import annotations

from pathlib import Path
from typing import Callable

from agent.paths import (
    LAB_DIR,
    TEST_DISK_PATH,
    ensure_runtime_directories,
)


CHUNK_SIZE = 1024 * 1024  # 1 MB

ProgressCallback = Callable[[int], None]


class VerificationError(Exception):
    """Raised when fake-disk verification cannot be completed."""


def validate_test_disk() -> Path:
    """Allow verification only for DataRakshak's fake test disk."""

    ensure_runtime_directories()

    allowed_lab_folder = LAB_DIR.resolve()
    test_disk = TEST_DISK_PATH.resolve()

    if not test_disk.exists():
        raise FileNotFoundError(
            "Fake test disk was not found. "
            "Create and wipe the fake test disk first."
        )

    if not test_disk.is_file():
        raise VerificationError(
            "The fake test-disk path is not a file."
        )

    if test_disk.parent != allowed_lab_folder:
        raise VerificationError(
            "Safety protection blocked verification. "
            "Only files inside the DataRakshak lab folder are allowed."
        )

    if test_disk.name != "test_disk.img":
        raise VerificationError(
            "Safety protection blocked verification. "
            "Only test_disk.img is allowed."
        )

    return test_disk


def verify_test_disk(
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """Verify that the complete fake disk contains only zero bytes."""

    test_disk = validate_test_disk()

    total_size = test_disk.stat().st_size

    if total_size <= 0:
        raise VerificationError(
            "The fake test disk is empty."
        )

    checked_size = 0
    failed_position: int | None = None
    previous_progress = -1

    try:
        with test_disk.open("rb") as disk:
            while True:
                data = disk.read(CHUNK_SIZE)

                if not data:
                    break

                for byte_index, byte_value in enumerate(data):
                    if byte_value != 0:
                        failed_position = (
                            checked_size + byte_index
                        )
                        break

                if failed_position is not None:
                    break

                checked_size += len(data)

                progress = int(
                    (checked_size / total_size) * 100
                )

                progress = min(
                    progress,
                    100,
                )

                if progress != previous_progress:
                    if progress_callback is not None:
                        progress_callback(progress)
                    else:
                        print(
                            (
                                "\rVerification progress: "
                                f"{progress}%"
                            ),
                            end="",
                            flush=True,
                        )

                    previous_progress = progress

    except OSError as error:
        raise VerificationError(
            f"Fake-disk verification failed: {error}"
        ) from error

    if progress_callback is None:
        print()

    if failed_position is not None:
        final_progress = int(
            (checked_size / total_size) * 100
        )

        return {
            "status": "failed",
            "message": "Non-zero data was found.",
            "failed_position": failed_position,
            "checked_bytes": checked_size,
            "total_bytes": total_size,
            "final_progress": final_progress,
        }

    if checked_size != total_size:
        raise VerificationError(
            "Verification ended before the complete disk was checked."
        )

    return {
        "status": "passed",
        "message": (
            "The complete fake test disk contains only zero bytes."
        ),
        "checked_bytes": checked_size,
        "total_bytes": total_size,
        "final_progress": 100,
    }


if __name__ == "__main__":
    result = verify_test_disk()

    print("Verification completed")
    print("Status:", result["status"])
    print("Checked bytes:", result["checked_bytes"])
    print("Total bytes:", result["total_bytes"])
    print("Final progress:", result["final_progress"])

    if result["status"] == "failed":
        print(
            "Failed position:",
            result["failed_position"],
        )