import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from agent.services.certificate_service import generate_certificate
from agent.services.verifier import verify_test_disk
from agent.services.wipe_engine import wipe_test_disk


TEST_DISK_PATH = Path("lab/test_disk.img")
TEST_DISK_SIZE = 10 * 1024 * 1024  # 10 MB


class DataRakshakWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.verification_passed = False

        self.setWindowTitle("DataRakshak")
        self.setMinimumSize(750, 700)

        title = QLabel("DataRakshak")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            """
            font-size: 36px;
            font-weight: bold;
            color: #14b8a6;
            """
        )

        subtitle = QLabel(
            "Secure Data Wiping and Verification Platform"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            """
            font-size: 18px;
            color: white;
            """
        )

        self.status_label = QLabel("System Status: Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(110)
        self.status_label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #111827;
                padding: 15px;
                background-color: #dcfce7;
                border: 2px solid #22c55e;
                border-radius: 8px;
            }
            """
        )

        self.create_disk_button = self.create_button(
            "1. Create Fake Test Disk",
            "#2563eb",
            "#1d4ed8",
        )

        self.wipe_button = self.create_button(
            "2. Securely Wipe Fake Disk",
            "#dc2626",
            "#b91c1c",
        )

        self.verify_button = self.create_button(
            "3. Verify Wipe Result",
            "#16a34a",
            "#15803d",
        )

        self.certificate_button = self.create_button(
            "4. Generate PDF Certificate",
            "#7c3aed",
            "#6d28d9",
        )

        self.certificate_button.setEnabled(False)

        self.create_disk_button.clicked.connect(
            self.create_fake_test_disk
        )

        self.wipe_button.clicked.connect(
            self.start_fake_disk_wipe
        )

        self.verify_button.clicked.connect(
            self.start_verification
        )

        self.certificate_button.clicked.connect(
            self.create_certificate
        )

        layout = QVBoxLayout()
        layout.setSpacing(18)
        layout.setContentsMargins(80, 45, 80, 45)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.create_disk_button)
        layout.addWidget(self.wipe_button)
        layout.addWidget(self.verify_button)
        layout.addWidget(self.certificate_button)
        layout.addStretch()

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def create_button(
        self,
        text: str,
        background_color: str,
        hover_color: str,
    ) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumHeight(50)

        button.setStyleSheet(
            f"""
            QPushButton {{
                font-size: 16px;
                font-weight: bold;
                background-color: {background_color};
                color: white;
                border: none;
                border-radius: 8px;
            }}

            QPushButton:hover {{
                background-color: {hover_color};
            }}

            QPushButton:disabled {{
                background-color: #6b7280;
            }}
            """
        )

        return button

    def set_operation_buttons_enabled(
        self,
        enabled: bool,
    ) -> None:
        self.create_disk_button.setEnabled(enabled)
        self.wipe_button.setEnabled(enabled)
        self.verify_button.setEnabled(enabled)

        if enabled:
            self.certificate_button.setEnabled(
                self.verification_passed
            )
        else:
            self.certificate_button.setEnabled(False)

    def create_fake_test_disk(self) -> None:
        self.set_operation_buttons_enabled(False)
        self.verification_passed = False

        self.status_label.setText(
            "Creating fake test disk...\nPlease wait."
        )

        QApplication.processEvents()

        try:
            TEST_DISK_PATH.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            TEST_DISK_PATH.write_bytes(
                b"A" * TEST_DISK_SIZE
            )

            size = TEST_DISK_PATH.stat().st_size

            self.status_label.setText(
                "Fake test disk created successfully ✅\n"
                f"Location: {TEST_DISK_PATH}\n"
                f"Size: {size} bytes"
            )

        except OSError as error:
            self.status_label.setText(
                "Fake disk creation failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_operation_buttons_enabled(True)

    def start_fake_disk_wipe(self) -> None:
        if not TEST_DISK_PATH.exists():
            self.status_label.setText(
                "Fake test disk not found ❌\n"
                "First click: Create Fake Test Disk"
            )
            return

        self.set_operation_buttons_enabled(False)
        self.verification_passed = False

        self.status_label.setText(
            "Secure wipe is running...\nPlease wait."
        )

        QApplication.processEvents()

        try:
            result = wipe_test_disk()

            self.status_label.setText(
                "Secure wipe completed successfully ✅\n"
                f"Written bytes: {result['written_bytes']}\n"
                f"Status: {result['status']}"
            )

        except (OSError, ValueError, FileNotFoundError) as error:
            self.status_label.setText(
                "Secure wipe failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_operation_buttons_enabled(True)

    def start_verification(self) -> None:
        if not TEST_DISK_PATH.exists():
            self.status_label.setText(
                "Fake test disk not found ❌\n"
                "First click: Create Fake Test Disk"
            )
            return

        self.set_operation_buttons_enabled(False)
        self.verification_passed = False

        self.status_label.setText(
            "Verification is running...\n"
            "Checking the complete fake disk."
        )

        QApplication.processEvents()

        try:
            result = verify_test_disk()

            if result["status"] == "passed":
                self.verification_passed = True

                self.status_label.setText(
                    "Verification passed successfully ✅\n"
                    "The complete fake disk contains only zero bytes.\n"
                    f"Checked bytes: {result['checked_bytes']}"
                )

            else:
                self.status_label.setText(
                    "Verification failed ❌\n"
                    "Non-zero data was found.\n"
                    f"Failed position: {result['failed_position']}"
                )

        except (OSError, ValueError, FileNotFoundError) as error:
            self.status_label.setText(
                "Verification failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_operation_buttons_enabled(True)

    def create_certificate(self) -> None:
        if not self.verification_passed:
            self.status_label.setText(
                "Certificate cannot be generated ❌\n"
                "Complete verification successfully first."
            )
            return

        self.set_operation_buttons_enabled(False)

        self.status_label.setText(
            "Generating PDF certificate...\nPlease wait."
        )

        QApplication.processEvents()

        try:
            result = generate_certificate(
                device_name="Fake Test Disk",
                serial_number="TEST-DISK-0001",
                total_bytes=TEST_DISK_PATH.stat().st_size,
                wipe_method="Single-pass zero overwrite",
                verification_status="PASSED",
            )

            self.status_label.setText(
                "PDF certificate generated successfully ✅\n"
                f"Certificate: {result['certificate_number']}\n"
                f"PDF: {result['pdf_path']}"
            )

        except OSError as error:
            self.status_label.setText(
                "Certificate generation failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_operation_buttons_enabled(True)


def start_application() -> None:
    app = QApplication(sys.argv)

    window = DataRakshakWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    start_application()