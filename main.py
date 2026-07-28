from __future__ import annotations

from agent.paths import ensure_runtime_directories


def main() -> None:
    """Start the DataRakshak desktop application."""

    print("DataRakshak project started successfully")

    try:
        ensure_runtime_directories()

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