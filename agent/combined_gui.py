from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from agent.gui import DataRakshakWindow
from agent.services.device_detector import (
    DeviceDetectionError,
    get_usb_disks,
)


class CombinedDataRakshakWindow(
    DataRakshakWindow
):
    """DataRakshak window supporting lab mode and USB detection."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(
            "DataRakshak — Lab and USB Mode"
        )

        self.resize(
            850,
            1040,
        )

        self.usb_button = self.make_button(
            "8. Detect USB Storage Devices (Read Only)",
            "#475569",
            "#334155",
        )

        self.usb_button.clicked.connect(
            self.detect_usb_devices
        )

        central_layout = (
            self.centralWidget().layout()
        )

        central_layout.addWidget(
            self.usb_button
        )

    def set_busy(
        self,
        busy: bool,
    ) -> None:
        """Disable all controls while an operation runs."""

        super().set_busy(busy)

        if hasattr(
            self,
            "usb_button",
        ):
            self.usb_button.setEnabled(
                not busy
            )

    def detect_usb_devices(self) -> None:
        """Detect USB storage devices without modifying them."""

        if self.is_operation_running():
            QMessageBox.information(
                self,
                "Operation Running",
                (
                    "Wait for the current wipe or "
                    "verification operation to finish."
                ),
            )
            return

        self.reset_progress(
            "USB Detection — Read Only"
        )

        self.set_busy(True)

        self.status_label.setText(
            "Scanning for USB storage devices...\n"
            "No drive will be modified."
        )

        QApplication.processEvents()

        try:
            usb_disks = get_usb_disks()

            self.progress_bar.setValue(100)

            if not usb_disks:
                self.status_label.setText(
                    "No USB storage device detected.\n\n"
                    "Fake Test Disk mode is still available ✅"
                )

                QMessageBox.information(
                    self,
                    "No USB Detected",
                    (
                        "No USB storage device was detected.\n\n"
                        "You can continue using:\n"
                        "• Create Fake Test Disk\n"
                        "• Securely Wipe Fake Disk\n"
                        "• Verify Wipe Result\n"
                        "• Generate Certificate\n\n"
                        "No physical drive was modified."
                    ),
                )
                return

            self.status_label.setText(
                "USB storage device detected safely ✅\n"
                f"Devices found: {len(usb_disks)}\n"
                "Mode: Read-only detection"
            )

            self.show_usb_devices(
                usb_disks
            )

        except DeviceDetectionError as error:
            self.status_label.setText(
                "USB device detection failed ❌\n"
                f"Error: {error}"
            )

            QMessageBox.critical(
                self,
                "USB Detection Error",
                str(error),
            )

        except Exception as error:
            self.status_label.setText(
                "Unexpected USB detection error ❌\n"
                f"Error: {error}"
            )

            QMessageBox.critical(
                self,
                "Unexpected Error",
                str(error),
            )

        finally:
            self.set_busy(False)

    def show_usb_devices(
        self,
        usb_disks: list[dict[str, Any]],
    ) -> None:
        """Display detected USB devices in a read-only table."""

        dialog = QDialog(self)

        dialog.setWindowTitle(
            "Detected USB Storage Devices"
        )

        dialog.resize(
            1100,
            480,
        )

        information_label = QLabel(
            (
                "USB storage devices detected in "
                "READ-ONLY mode. No data was erased."
            )
        )

        information_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        information_label.setWordWrap(True)

        information_label.setStyleSheet(
            """
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: white;
                background-color: #0f766e;
                border-radius: 8px;
                padding: 12px;
            }
            """
        )

        table = QTableWidget()

        table.setRowCount(
            len(usb_disks)
        )

        table.setColumnCount(8)

        table.setHorizontalHeaderLabels(
            [
                "Disk Index",
                "Physical Device",
                "Model",
                "Serial Number",
                "Capacity",
                "Interface",
                "Status",
                "Safety Mode",
            ]
        )

        for row_number, disk in enumerate(
            usb_disks
        ):
            values = [
                disk.get("index"),
                disk.get("device_id"),
                disk.get("model"),
                disk.get("serial_number"),
                disk.get("size_display"),
                disk.get("interface_type"),
                disk.get("status"),
                disk.get("access_mode"),
            ]

            for column_number, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    (
                        ""
                        if value is None
                        else str(value)
                    )
                )

                item.setFlags(
                    item.flags()
                    & ~Qt.ItemFlag.ItemIsEditable
                )

                table.setItem(
                    row_number,
                    column_number,
                    item,
                )

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        table.setAlternatingRowColors(True)

        warning_label = QLabel(
            (
                "Safety Protection: Real USB wiping is "
                "disabled in this prototype. The detected "
                "device information is displayed only."
            )
        )

        warning_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        warning_label.setWordWrap(True)

        warning_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #7f1d1d;
                background-color: #fee2e2;
                border: 1px solid #ef4444;
                border-radius: 8px;
                padding: 10px;
            }
            """
        )

        layout = QVBoxLayout()

        layout.addWidget(
            information_label
        )

        layout.addWidget(
            table
        )

        layout.addWidget(
            warning_label
        )

        dialog.setLayout(
            layout
        )

        dialog.setStyleSheet(
            """
            QDialog {
                background-color: #0f172a;
            }

            QTableWidget {
                background-color: white;
                color: #111827;
                gridline-color: #cbd5e1;
            }

            QHeaderView::section {
                background-color: #475569;
                color: white;
                font-weight: bold;
                padding: 7px;
            }
            """
        )

        dialog.exec()


def start_application() -> None:
    """Start the unified DataRakshak application."""

    app = QApplication(sys.argv)

    window = CombinedDataRakshakWindow()
    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    start_application()