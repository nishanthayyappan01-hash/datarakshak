from pathlib import Path


TEST_DISK_PATH = Path("lab/test_disk.img").resolve()
CHUNK_SIZE = 1024 * 1024  # 1 MB


def wipe_test_disk() -> dict:
    """Safely overwrite only the project's fake test disk with zeros."""

    if not TEST_DISK_PATH.exists():
        raise FileNotFoundError(
            "lab/test_disk.img file not found. Create the test disk first."
        )

    if not TEST_DISK_PATH.is_file():
        raise ValueError("The test disk path is not a file.")

    if TEST_DISK_PATH.name != "test_disk.img":
        raise ValueError("Only test_disk.img is allowed.")

    total_size = TEST_DISK_PATH.stat().st_size
    written_size = 0

    zero_chunk = b"\x00" * CHUNK_SIZE

    with TEST_DISK_PATH.open("r+b") as disk:
        while written_size < total_size:
            remaining_size = total_size - written_size
            current_size = min(CHUNK_SIZE, remaining_size)

            disk.write(zero_chunk[:current_size])
            written_size += current_size

            progress = (written_size / total_size) * 100
            print(f"\rWiping progress: {progress:.0f}%", end="")

    print()

    return {
        "status": "completed",
        "file": str(TEST_DISK_PATH),
        "total_bytes": total_size,
        "written_bytes": written_size,
    }


if __name__ == "__main__":
    result = wipe_test_disk()
    print(result)