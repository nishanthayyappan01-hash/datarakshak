import json
import unittest
from unittest.mock import patch

from agent.services.device_detector import (
    DeviceDetectionError,
    format_size,
    get_all_physical_disks,
    get_usb_disks,
    normalize_serial_number,
)


class DeviceDetectorTests(unittest.TestCase):
    def test_format_size(self) -> None:
        self.assertEqual(
            format_size(0),
            "0.00 bytes",
        )

        self.assertEqual(
            format_size(1024),
            "1.00 KB",
        )

        self.assertEqual(
            format_size(1024 * 1024),
            "1.00 MB",
        )

        self.assertEqual(
            format_size(16 * 1024 * 1024 * 1024),
            "16.00 GB",
        )

    def test_normalize_serial_number(self) -> None:
        self.assertEqual(
            normalize_serial_number(None),
            "UNKNOWN",
        )

        self.assertEqual(
            normalize_serial_number(""),
            "UNKNOWN",
        )

        self.assertEqual(
            normalize_serial_number("  USB-12345  "),
            "USB-12345",
        )

    @patch(
        "agent.services.device_detector.run_powershell"
    )
    def test_empty_device_output(
        self,
        mocked_powershell,
    ) -> None:
        mocked_powershell.return_value = ""

        disks = get_all_physical_disks()

        self.assertEqual(
            disks,
            [],
        )

    @patch(
        "agent.services.device_detector.run_powershell"
    )
    def test_usb_filter_returns_only_usb_device(
        self,
        mocked_powershell,
    ) -> None:
        simulated_devices = [
            {
                "Index": 0,
                "DeviceID": r"\\.\PHYSICALDRIVE0",
                "Model": "Internal SSD",
                "Manufacturer": "Example Manufacturer",
                "SerialNumber": "SSD-0001",
                "Size": 512 * 1024 * 1024 * 1024,
                "InterfaceType": "SCSI",
                "MediaType": "Fixed hard disk media",
                "PNPDeviceID": (
                    "SCSI\\DISK&VEN_INTERNAL"
                ),
                "Partitions": 3,
                "Status": "OK",
            },
            {
                "Index": 1,
                "DeviceID": r"\\.\PHYSICALDRIVE1",
                "Model": "Simulated USB Drive",
                "Manufacturer": "DataRakshak Lab",
                "SerialNumber": "USB-TEST-0001",
                "Size": 16 * 1024 * 1024 * 1024,
                "InterfaceType": "USB",
                "MediaType": "Removable Media",
                "PNPDeviceID": (
                    "USBSTOR\\DISK&VEN_DATARAKSHAK"
                ),
                "Partitions": 1,
                "Status": "OK",
            },
        ]

        mocked_powershell.return_value = json.dumps(
            simulated_devices
        )

        usb_disks = get_usb_disks()

        self.assertEqual(
            len(usb_disks),
            1,
        )

        detected_usb = usb_disks[0]

        self.assertEqual(
            detected_usb["device_id"],
            r"\\.\PHYSICALDRIVE1",
        )

        self.assertEqual(
            detected_usb["model"],
            "Simulated USB Drive",
        )

        self.assertEqual(
            detected_usb["serial_number"],
            "USB-TEST-0001",
        )

        self.assertEqual(
            detected_usb["size_display"],
            "16.00 GB",
        )

        self.assertTrue(
            detected_usb["is_usb"]
        )

        self.assertEqual(
            detected_usb["access_mode"],
            "READ_ONLY_DETECTION",
        )

    @patch(
        "agent.services.device_detector.run_powershell"
    )
    def test_usbstor_pnp_device_is_detected(
        self,
        mocked_powershell,
    ) -> None:
        simulated_device = {
            "Index": 2,
            "DeviceID": r"\\.\PHYSICALDRIVE2",
            "Model": "USB Storage Device",
            "Manufacturer": "Generic",
            "SerialNumber": None,
            "Size": 8 * 1024 * 1024 * 1024,
            "InterfaceType": "SCSI",
            "MediaType": "Removable Media",
            "PNPDeviceID": (
                "USBSTOR\\DISK&VEN_GENERIC"
            ),
            "Partitions": 1,
            "Status": "OK",
        }

        mocked_powershell.return_value = json.dumps(
            simulated_device
        )

        usb_disks = get_usb_disks()

        self.assertEqual(
            len(usb_disks),
            1,
        )

        self.assertEqual(
            usb_disks[0]["serial_number"],
            "UNKNOWN",
        )

        self.assertTrue(
            usb_disks[0]["is_usb"]
        )

    @patch(
        "agent.services.device_detector.run_powershell"
    )
    def test_invalid_windows_output(
        self,
        mocked_powershell,
    ) -> None:
        mocked_powershell.return_value = (
            "invalid-json-output"
        )

        with self.assertRaises(
            DeviceDetectionError
        ):
            get_all_physical_disks()


if __name__ == "__main__":
    unittest.main(verbosity=2)