from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def prepare_project() -> None:
    """Prepare required local folders before starting the GUI."""

    required_folders = [
        PROJECT_ROOT / "lab",
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "certificates",
        PROJECT_ROOT / "audit_logs",
        PROJECT_ROOT / "keys",
    ]

    for folder in required_folders:
        folder.mkdir(
            parents=True,
            exist_ok=True,
        )


def main() -> None:
    """Start the DataRakshak desktop application."""

    print("DataRakshak project started successfully")

    try:
        prepare_project()

        from agent.gui import start_application

        start_application()

    except KeyboardInterrupt:
        print(
            "\nDataRakshak was closed by the user."
        )

    except Exception as error:
        print(
            "DataRakshak could not be started."
        )
        print(f"Error: {error}")

        raise SystemExit(1) from error


if __name__ == "__main__":
    main()