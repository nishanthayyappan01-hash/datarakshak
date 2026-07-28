from __future__ import annotations

import os
from pathlib import Path
from typing import Callable


TEST_DISK_PATH = Path("lab/test_disk.img").resolve()
CHUNK_SIZE = 1024 * 1024  # 1 MB

ProgressCallback = Callable[[int], None]


class WipeError(Exception):
    """Raised when the fake-disk wipe cannot be completed safely."""


def validate_test_disk() -> Path:
    """Allow only the project's fake test disk."""

    project_folder = Path.cwd().resolve()
    allowed_lab_folder = (
        project_folder / "lab"
    ).resolve()

    test_disk = TEST_DISK_PATH.resolve()

    if not test_disk.exists():
        raise FileNotFoundError(
            "lab/test_disk.img was not found. "
            "Create the fake test disk first."
        )

    if not test_disk.is_file():
        raise WipeError(
            "The fake test-disk path is not a file."
        )

    if test_disk.parent != allowed_lab_folder:
        raise WipeError(
            "Safety protection blocked the wipe. "
            "Only files inside the lab folder are allowed."
        )

    if test_disk.name != "test_disk.img":
        raise WipeError(
            "Safety protection blocked the wipe. "
            "Only test_disk.img is allowed."
        )

    return test_disk


def wipe_test_disk(
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """Overwrite the complete fake test disk with zero bytes."""

    test_disk = validate_test_disk()

    total_size = test_disk.stat().st_size

    if total_size <= 0:
        raise WipeError(
            "The fake test disk is empty."
        )

    written_size = 0
    previous_progress = -1

    zero_chunk = b"\x00" * CHUNK_SIZE

    try:
        with test_disk.open(
            "r+b",
            buffering=0,
        ) as disk:
            while written_size < total_size:
                remaining_size = (
                    total_size - written_size
                )

                current_size = min(
                    CHUNK_SIZE,
                    remaining_size,
                )

                disk.write(
                    zero_chunk[:current_size]
                )

                written_size += current_size

                progress = int(
                    (written_size / total_size) * 100
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
                            f"\rWiping progress: {progress}%",
                            end="",
                            flush=True,
                        )

                    previous_progress = progress

            disk.flush()
            os.fsync(disk.fileno())

    except OSError as error:
        raise WipeError(
            f"Fake-disk wipe failed: {error}"
        ) from error

    if progress_callback is None:
        print()

    return {
        "status": "completed",
        "file": str(test_disk),
        "total_bytes": total_size,
        "written_bytes": written_size,
        "wipe_method": "Single-pass zero overwrite",
        "final_progress": 100,
    }


if __name__ == "__main__":
    result = wipe_test_disk()

    print("Wipe completed successfully")
    print("Target:", result["file"])
    print("Total bytes:", result["total_bytes"])
    print("Written bytes:", result["written_bytes"])
    print("Status:", result["status"])