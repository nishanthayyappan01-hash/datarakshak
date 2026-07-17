from pathlib import Path


TEST_DISK_PATH = Path("lab/test_disk.img").resolve()
CHUNK_SIZE = 1024 * 1024  # 1 MB


def verify_test_disk() -> dict:
    """Check whether the complete fake test disk contains only zero bytes."""

    if not TEST_DISK_PATH.exists():
        raise FileNotFoundError(
            "lab/test_disk.img file not found."
        )

    if not TEST_DISK_PATH.is_file():
        raise ValueError("The test disk path is not a file.")

    total_size = TEST_DISK_PATH.stat().st_size
    checked_size = 0
    failed_position = None

    with TEST_DISK_PATH.open("rb") as disk:
        while True:
            data = disk.read(CHUNK_SIZE)

            if not data:
                break

            if data != b"\x00" * len(data):
                for index, byte in enumerate(data):
                    if byte != 0:
                        failed_position = checked_size + index
                        break

                break

            checked_size += len(data)

            progress = (checked_size / total_size) * 100
            print(f"\rVerification progress: {progress:.0f}%", end="")

    print()

    if failed_position is not None:
        return {
            "status": "failed",
            "message": "Non-zero data was found.",
            "failed_position": failed_position,
        }

    return {
        "status": "passed",
        "message": "The complete test disk contains only zero bytes.",
        "checked_bytes": checked_size,
    }


if __name__ == "__main__":
    result = verify_test_disk()
    print(result)