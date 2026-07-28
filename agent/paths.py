from __future__ import annotations

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return the application root in development and EXE modes."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()

LAB_DIR = PROJECT_ROOT / "lab"
DATA_DIR = PROJECT_ROOT / "data"
CERTIFICATES_DIR = PROJECT_ROOT / "certificates"
AUDIT_LOGS_DIR = PROJECT_ROOT / "audit_logs"
KEYS_DIR = PROJECT_ROOT / "keys"

TEST_DISK_PATH = LAB_DIR / "test_disk.img"
DATABASE_PATH = DATA_DIR / "datarakshak.db"
AUDIT_LOG_PATH = AUDIT_LOGS_DIR / "audit_log.jsonl"

PRIVATE_KEY_PATH = KEYS_DIR / "private_key.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "public_key.pem"


def ensure_runtime_directories() -> None:
    """Create folders required by the DataRakshak application."""

    required_directories = [
        LAB_DIR,
        DATA_DIR,
        CERTIFICATES_DIR,
        AUDIT_LOGS_DIR,
        KEYS_DIR,
    ]

    for directory in required_directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )