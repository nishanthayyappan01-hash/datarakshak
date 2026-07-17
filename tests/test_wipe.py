from pathlib import Path

from agent.services.verifier import verify_test_disk
from agent.services.wipe_engine import wipe_test_disk


TEST_DISK_PATH = Path("lab/test_disk.img")


def prepare_test_disk() -> None:
    """Fill the fake test disk with non-zero sample data."""

    disk_size = 10 * 1024 * 1024  # 10 MB
    sample_data = b"A" * disk_size

    TEST_DISK_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEST_DISK_PATH.write_bytes(sample_data)

    print("Fake test disk prepared.")
    print(f"Disk size: {TEST_DISK_PATH.stat().st_size} bytes")


def run_complete_test() -> None:
    print("\nSTEP 1: Preparing fake disk")
    prepare_test_disk()

    print("\nSTEP 2: Starting secure wipe")
    wipe_result = wipe_test_disk()
    print("Wipe result:", wipe_result)

    print("\nSTEP 3: Starting verification")
    verification_result = verify_test_disk()
    print("Verification result:", verification_result)

    if verification_result["status"] == "passed":
        print("\nTEST PASSED: Fake disk was wiped and verified successfully.")
    else:
        print("\nTEST FAILED: Non-zero data is still present.")


if __name__ == "__main__":
    run_complete_test()