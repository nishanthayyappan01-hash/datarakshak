from __future__ import annotations

import json
import subprocess
from typing import Any


class DeviceDetectionError(Exception):
    """Raised when Windows storage-device detection fails."""


def run_powershell(command: str) -> str:
    """Run a read-only PowerShell command and return its output."""

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )

    except FileNotFoundError as error:
        raise DeviceDetectionError(
            "PowerShell was not found on this computer."
        ) from error

    except subprocess.CalledProcessError as error:
        message = (
            error.stderr.strip()
            or error.stdout.strip()
            or "Unknown PowerShell error"
        )

        raise DeviceDetectionError(
            f"Device detection failed: {message}"
        ) from error

    return result.stdout.strip()


def normalize_serial_number(
    serial_number: Any,
) -> str:
    """Return a clean serial number or a safe fallback."""

    if serial_number is None:
        return "UNKNOWN"

    cleaned = str(serial_number).strip()

    return cleaned if cleaned else "UNKNOWN"


def format_size(
    size_bytes: int,
) -> str:
    """Convert bytes into a readable storage size."""

    if size_bytes < 0:
        return "Unknown"

    units = [
        "bytes",
        "KB",
        "MB",
        "GB",
        "TB",
    ]

    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"


def get_all_physical_disks() -> list[dict[str, Any]]:
    """Read Windows physical-disk information without modifying devices."""

    powershell_command = """
    Get-CimInstance Win32_DiskDrive |
    Select-Object `
        Index,
        DeviceID,
        Model,
        Manufacturer,
        SerialNumber,
        Size,
        InterfaceType,
        MediaType,
        PNPDeviceID,
        Partitions,
        Status |
    ConvertTo-Json -Depth 4 -Compress
    """

    output = run_powershell(
        powershell_command
    )

    if not output:
        return []

    try:
        parsed_data = json.loads(output)

    except json.JSONDecodeError as error:
        raise DeviceDetectionError(
            "Windows returned invalid device information."
        ) from error

    if isinstance(parsed_data, dict):
        raw_disks = [parsed_data]

    elif isinstance(parsed_data, list):
        raw_disks = parsed_data

    else:
        raise DeviceDetectionError(
            "Unexpected physical-disk information format."
        )

    disks: list[dict[str, Any]] = []

    for raw_disk in raw_disks:
        size_value = raw_disk.get("Size")

        try:
            size_bytes = int(size_value or 0)
        except (TypeError, ValueError):
            size_bytes = 0

        interface_type = str(
            raw_disk.get("InterfaceType") or "UNKNOWN"
        ).strip()

        pnp_device_id = str(
            raw_disk.get("PNPDeviceID") or ""
        ).strip()

        is_usb = (
            interface_type.upper() == "USB"
            or pnp_device_id.upper().startswith("USBSTOR")
        )

        disk = {
            "index": raw_disk.get("Index"),
            "device_id": str(
                raw_disk.get("DeviceID") or "UNKNOWN"
            ).strip(),
            "model": str(
                raw_disk.get("Model") or "Unknown Device"
            ).strip(),
            "manufacturer": str(
                raw_disk.get("Manufacturer") or "Unknown"
            ).strip(),
            "serial_number": normalize_serial_number(
                raw_disk.get("SerialNumber")
            ),
            "size_bytes": size_bytes,
            "size_display": format_size(size_bytes),
            "interface_type": interface_type,
            "media_type": str(
                raw_disk.get("MediaType") or "Unknown"
            ).strip(),
            "pnp_device_id": pnp_device_id,
            "partitions": raw_disk.get("Partitions"),
            "status": str(
                raw_disk.get("Status") or "Unknown"
            ).strip(),
            "is_usb": is_usb,
            "access_mode": "READ_ONLY_DETECTION",
        }

        disks.append(disk)

    return disks


def get_usb_disks() -> list[dict[str, Any]]:
    """Return only USB-connected physical disks."""

    return [
        disk
        for disk in get_all_physical_disks()
        if disk["is_usb"]
    ]


def print_usb_disks(
    usb_disks: list[dict[str, Any]],
) -> None:
    """Display detected USB storage devices."""

    print("\nDataRakshak USB Device Detection")
    print("--------------------------------")

    if not usb_disks:
        print("No USB storage device detected.")
        print("Connect a pen drive and run this command again.")
        return

    print(
        f"Detected USB storage devices: {len(usb_disks)}"
    )

    for number, disk in enumerate(
        usb_disks,
        start=1,
    ):
        print(f"\nUSB Device {number}")
        print("----------------")

        print(
            "Physical device:",
            disk["device_id"],
        )

        print(
            "Model:",
            disk["model"],
        )

        print(
            "Manufacturer:",
            disk["manufacturer"],
        )

        print(
            "Serial number:",
            disk["serial_number"],
        )

        print(
            "Capacity:",
            disk["size_display"],
        )

        print(
            "Interface:",
            disk["interface_type"],
        )

        print(
            "Media type:",
            disk["media_type"],
        )

        print(
            "Partitions:",
            disk["partitions"],
        )

        print(
            "Device status:",
            disk["status"],
        )

        print(
            "Safety mode:",
            disk["access_mode"],
        )


def main() -> None:
    """Detect connected USB storage devices safely."""

    try:
        usb_disks = get_usb_disks()

        print_usb_disks(
            usb_disks
        )

        print(
            "\nSafety notice: "
            "This module only reads device information. "
            "It does not erase or modify any drive."
        )

    except DeviceDetectionError as error:
        print(
            "USB device detection failed:"
        )

        print(error)

        raise SystemExit(1) from error


if __name__ == "__main__":
    main()