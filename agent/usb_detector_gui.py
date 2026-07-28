import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from agent.services.device_detector import (
    DeviceDetectionError,
    get_usb_disks,
)


class USBDetectorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("DataRakshak USB Detector")
        self.resize(650, 500)

        title = QLabel("USB Device Detection")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            """
            font-size: 30px;
            font-weight: bold;
            color: #14b8a6;
            background: transparent;
            """
        )

        subtitle = QLabel(
            "Read-only device detection — no data will be erased"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            """
            font-size: 15px;
            color: white;
            background: transparent;
            """
        )

        self.result_label = QLabel(
            "Click the button to scan for USB storage devices."
        )
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setWordWrap(True)
        self.result_label.setMinimumHeight(230)
        self.result_label.setStyleSheet(
            """
            QLabel {
                font-size: 15px;
                color: #111827;
                background-color: #f8fafc;
                border: 2px solid #14b8a6;
                border-radius: 10px;
                padding: 20px;
            }
            """
        )

        self.detect_button = QPushButton(
            "Detect USB Devices"
        )
        self.detect_button.setMinimumHeight(55)
        self.detect_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.detect_button.setStyleSheet(
            """
            QPushButton {
                font-size: 17px;
                font-weight: bold;
                color: white;
                background-color: #2563eb;
                border: none;
                border-radius: 9px;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton:disabled {
                background-color: #64748b;
            }
            """
        )

        self.detect_button.clicked.connect(
            self.detect_usb_devices
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(60, 50, 60, 50)
        layout.setSpacing(20)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.result_label)
        layout.addWidget(self.detect_button)

        container = QWidget()
        container.setLayout(layout)
        container.setStyleSheet(
            """
            QWidget {
                background-color: #0f172a;
            }
            """
        )

        self.setCentralWidget(container)

    def detect_usb_devices(self) -> None:
        self.detect_button.setEnabled(False)

        self.result_label.setText(
            "Scanning for USB storage devices..."
        )

        QApplication.processEvents()

        try:
            usb_disks = get_usb_disks()

            if not usb_disks:
                self.result_label.setText(
                    "No USB storage device detected.\n\n"
                    "This is normal because no pen drive is connected.\n\n"
                    "Status: Detection module is working safely ✅"
                )
                return

            device_details: list[str] = []

            for number, disk in enumerate(
                usb_disks,
                start=1,
            ):
                details = (
                    f"USB Device {number}\n"
                    f"Model: {disk['model']}\n"
                    f"Serial: {disk['serial_number']}\n"
                    f"Capacity: {disk['size_display']}\n"
                    f"Interface: {disk['interface_type']}\n"
                    f"Status: {disk['status']}\n"
                    f"Safety: {disk['access_mode']}"
                )

                device_details.append(details)

            self.result_label.setText(
                "\n\n".join(device_details)
            )

        except DeviceDetectionError as error:
            self.result_label.setText(
                "USB detection failed ❌\n\n"
                f"Error: {error}"
            )

        except Exception as error:
            self.result_label.setText(
                "Unexpected detection error ❌\n\n"
                f"Error: {error}"
            )

        finally:
            self.detect_button.setEnabled(True)


def start_application() -> None:
    app = QApplication(sys.argv)

    window = USBDetectorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    start_application()