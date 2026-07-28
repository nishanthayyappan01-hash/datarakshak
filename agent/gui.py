import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from agent.services.audit_logger import verify_audit_log, write_audit_log
from agent.services.certificate_service import generate_certificate
from agent.services.verifier import verify_test_disk
from agent.services.wipe_engine import wipe_test_disk


TEST_DISK_PATH = Path("lab/test_disk.img")
TEST_DISK_SIZE = 10 * 1024 * 1024


class DataRakshakWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.verification_passed = False

        self.setWindowTitle("DataRakshak")
        self.resize(760, 760)

        self.title_label = QLabel("DataRakshak")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            """
            font-size: 38px;
            font-weight: bold;
            color: #14b8a6;
            background: transparent;
            """
        )

        self.subtitle_label = QLabel(
            "Secure Data Wiping and Verification Platform"
        )
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet(
            """
            font-size: 18px;
            color: white;
            background: transparent;
            """
        )

        self.status_label = QLabel("System Status: Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(120)
        self.status_label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #111827;
                background-color: #f0fdf4;
                border: 2px solid #22c55e;
                border-radius: 10px;
                padding: 15px;
            }
            """
        )

        self.create_disk_button = self.make_button(
            "1. Create Fake Test Disk",
            "#2563eb",
            "#1d4ed8",
        )

        self.wipe_button = self.make_button(
            "2. Securely Wipe Fake Disk",
            "#dc2626",
            "#b91c1c",
        )

        self.verify_button = self.make_button(
            "3. Verify Wipe Result",
            "#16a34a",
            "#15803d",
        )

        self.certificate_button = self.make_button(
            "4. Generate PDF Certificate",
            "#7c3aed",
            "#6d28d9",
        )

        self.audit_button = self.make_button(
            "5. Verify Audit Log",
            "#ea580c",
            "#c2410c",
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
        self.audit_button.clicked.connect(
            self.check_audit_log
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(80, 45, 80, 45)
        layout.setSpacing(17)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(25)
        layout.addWidget(self.status_label)
        layout.addWidget(self.create_disk_button)
        layout.addWidget(self.wipe_button)
        layout.addWidget(self.verify_button)
        layout.addWidget(self.certificate_button)
        layout.addWidget(self.audit_button)

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

    def make_button(
        self,
        text: str,
        normal_color: str,
        hover_color: str,
    ) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumHeight(55)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        button.setStyleSheet(
            f"""
            QPushButton {{
                font-size: 16px;
                font-weight: bold;
                color: white;
                background-color: {normal_color};
                border: none;
                border-radius: 9px;
            }}

            QPushButton:hover {{
                background-color: {hover_color};
            }}

            QPushButton:pressed {{
                padding-top: 3px;
            }}

            QPushButton:disabled {{
                background-color: #9ca3af;
                color: #e5e7eb;
            }}
            """
        )

        return button

    def set_busy(self, busy: bool) -> None:
        enabled = not busy

        self.create_disk_button.setEnabled(enabled)
        self.wipe_button.setEnabled(enabled)
        self.verify_button.setEnabled(enabled)
        self.audit_button.setEnabled(enabled)

        if busy:
            self.certificate_button.setEnabled(False)
        else:
            self.certificate_button.setEnabled(
                self.verification_passed
            )

        QApplication.processEvents()

    def create_fake_test_disk(self) -> None:
        self.verification_passed = False
        self.set_busy(True)

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

            write_audit_log(
                action="CREATE_FAKE_TEST_DISK",
                status="SUCCESS",
                details={
                    "path": str(TEST_DISK_PATH),
                    "size_bytes": size,
                },
            )

            self.status_label.setText(
                "Fake test disk created successfully ✅\n"
                f"Location: {TEST_DISK_PATH}\n"
                f"Size: {size} bytes"
            )

        except Exception as error:
            self.status_label.setText(
                "Fake disk creation failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_busy(False)

    def start_fake_disk_wipe(self) -> None:
        if not TEST_DISK_PATH.exists():
            QMessageBox.information(
                self,
                "Test Disk Missing",
                "First click 'Create Fake Test Disk'.",
            )
            return

        confirmation = QMessageBox.question(
            self,
            "Confirm Secure Wipe",
            (
                "All data inside the fake test disk will be erased.\n\n"
                f"Target: {TEST_DISK_PATH}\n"
                f"Size: {TEST_DISK_PATH.stat().st_size} bytes\n\n"
                "Continue?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            write_audit_log(
                action="WIPE_FAKE_TEST_DISK",
                status="CANCELLED",
                details={
                    "reason": "User cancelled operation",
                },
            )

            self.status_label.setText(
                "Secure wipe cancelled by user."
            )
            return

        self.verification_passed = False
        self.set_busy(True)

        self.status_label.setText(
            "Secure wipe is running...\nPlease wait."
        )
        QApplication.processEvents()

        try:
            result = wipe_test_disk()

            write_audit_log(
                action="WIPE_FAKE_TEST_DISK",
                status="SUCCESS",
                details={
                    "written_bytes": result["written_bytes"],
                    "wipe_status": result["status"],
                },
            )

            self.status_label.setText(
                "Secure wipe completed successfully ✅\n"
                f"Written bytes: {result['written_bytes']}\n"
                f"Status: {result['status']}"
            )

        except Exception as error:
            self.status_label.setText(
                "Secure wipe failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_busy(False)

    def start_verification(self) -> None:
        if not TEST_DISK_PATH.exists():
            QMessageBox.information(
                self,
                "Test Disk Missing",
                "First click 'Create Fake Test Disk'.",
            )
            return

        self.verification_passed = False
        self.set_busy(True)

        self.status_label.setText(
            "Verification is running...\n"
            "Checking complete fake disk."
        )
        QApplication.processEvents()

        try:
            result = verify_test_disk()

            if result["status"] == "passed":
                self.verification_passed = True

                write_audit_log(
                    action="VERIFY_WIPE_RESULT",
                    status="SUCCESS",
                    details={
                        "checked_bytes": result["checked_bytes"],
                    },
                )

                self.status_label.setText(
                    "Verification passed successfully ✅\n"
                    "The fake disk contains only zero bytes.\n"
                    f"Checked bytes: {result['checked_bytes']}"
                )

            else:
                write_audit_log(
                    action="VERIFY_WIPE_RESULT",
                    status="FAILED",
                    details={
                        "failed_position": result[
                            "failed_position"
                        ],
                    },
                )

                self.status_label.setText(
                    "Verification failed ❌\n"
                    "Non-zero data was found.\n"
                    f"Position: {result['failed_position']}"
                )

        except Exception as error:
            self.status_label.setText(
                "Verification failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_busy(False)

    def create_certificate(self) -> None:
        if not self.verification_passed:
            QMessageBox.information(
                self,
                "Verification Required",
                "Complete wipe verification first.",
            )
            return

        self.set_busy(True)

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

            write_audit_log(
                action="GENERATE_CERTIFICATE",
                status="SUCCESS",
                details={
                    "certificate_number": result[
                        "certificate_number"
                    ],
                    "certificate_hash": result[
                        "certificate_hash"
                    ],
                },
            )

            self.status_label.setText(
                "PDF certificate generated successfully ✅\n"
                f"Certificate: {result['certificate_number']}\n"
                f"PDF: {result['pdf_path']}"
            )

            QMessageBox.information(
                self,
                "Certificate Created",
                (
                    "PDF certificate generated successfully.\n\n"
                    f"{result['pdf_path']}"
                ),
            )

        except Exception as error:
            self.status_label.setText(
                "Certificate generation failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_busy(False)

    def check_audit_log(self) -> None:
        self.set_busy(True)

        self.status_label.setText(
            "Verifying audit-log hash chain...\nPlease wait."
        )
        QApplication.processEvents()

        try:
            result = verify_audit_log()

            if result["status"] == "passed":
                self.status_label.setText(
                    "Audit log verification passed ✅\n"
                    "No audit entries were modified.\n"
                    f"Entries checked: {result['entries_checked']}"
                )

            elif result["status"] == "empty":
                self.status_label.setText(
                    "Audit log is empty.\n"
                    "Complete an operation first."
                )

            else:
                self.status_label.setText(
                    "Audit log verification failed ❌\n"
                    f"Reason: {result['message']}"
                )

        except Exception as error:
            self.status_label.setText(
                "Audit log verification failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_busy(False)


def start_application() -> None:
    app = QApplication(sys.argv)

    window = DataRakshakWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    start_application()