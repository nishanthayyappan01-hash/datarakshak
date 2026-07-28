import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from agent.services.audit_logger import (
    verify_audit_log,
    write_audit_log,
)
from agent.services.certificate_service import generate_certificate
from agent.services.certificate_verifier import verify_certificate
from agent.services.database_service import (
    create_wipe_job,
    initialize_database,
    list_wipe_jobs,
    update_wipe_job,
)
from agent.services.verifier import verify_test_disk
from agent.services.wipe_engine import wipe_test_disk


TEST_DISK_PATH = Path("lab/test_disk.img")
TEST_DISK_SIZE = 10 * 1024 * 1024

DEVICE_NAME = "Fake Test Disk"
SERIAL_NUMBER = "TEST-DISK-0001"
WIPE_METHOD = "Single-pass zero overwrite"


class DataRakshakWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        initialize_database()

        self.verification_passed = False
        self.current_job_id: int | None = None
        self.current_job_number: str | None = None

        self.setWindowTitle("DataRakshak")
        self.resize(800, 900)

        self.title_label = QLabel("DataRakshak")
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
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
        self.subtitle_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.subtitle_label.setStyleSheet(
            """
            font-size: 18px;
            color: white;
            background: transparent;
            """
        )

        self.status_label = QLabel(
            "System Status: Ready"
        )
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(130)
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

        self.history_button = self.make_button(
            "6. View Wipe History",
            "#0891b2",
            "#0e7490",
        )

        self.certificate_verify_button = self.make_button(
            "7. Verify Certificate",
            "#be185d",
            "#9d174d",
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

        self.history_button.clicked.connect(
            self.show_wipe_history
        )

        self.certificate_verify_button.clicked.connect(
            self.verify_certificate_file
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(75, 35, 75, 35)
        layout.setSpacing(13)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(15)
        layout.addWidget(self.status_label)
        layout.addWidget(self.create_disk_button)
        layout.addWidget(self.wipe_button)
        layout.addWidget(self.verify_button)
        layout.addWidget(self.certificate_button)
        layout.addWidget(self.audit_button)
        layout.addWidget(self.history_button)
        layout.addWidget(self.certificate_verify_button)

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
        button.setMinimumHeight(50)
        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

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
        self.history_button.setEnabled(enabled)
        self.certificate_verify_button.setEnabled(enabled)

        if busy:
            self.certificate_button.setEnabled(False)
        else:
            self.certificate_button.setEnabled(
                self.verification_passed
            )

        QApplication.processEvents()

    def safe_audit(
        self,
        action: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        try:
            write_audit_log(
                action=action,
                status=status,
                details=details or {},
            )
        except Exception:
            pass

    def safely_update_job(
        self,
        **updates: Any,
    ) -> None:
        if self.current_job_id is None:
            return

        try:
            update_wipe_job(
                job_id=self.current_job_id,
                **updates,
            )
        except Exception:
            pass

    def create_fake_test_disk(self) -> None:
        self.verification_passed = False
        self.current_job_id = None
        self.current_job_number = None

        self.set_busy(True)

        self.status_label.setText(
            "Creating fake test disk...\n"
            "Please wait."
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

            self.safe_audit(
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
            self.safe_audit(
                action="CREATE_FAKE_TEST_DISK",
                status="FAILED",
                details={
                    "error": str(error),
                },
            )

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
                "All data inside the fake test disk "
                "will be erased.\n\n"
                f"Target: {TEST_DISK_PATH}\n"
                f"Size: {TEST_DISK_PATH.stat().st_size} bytes\n\n"
                "Continue?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            self.safe_audit(
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
            "Creating database wipe job...\n"
            "Please wait."
        )

        QApplication.processEvents()

        try:
            job = create_wipe_job(
                device_name=DEVICE_NAME,
                serial_number=SERIAL_NUMBER,
                total_bytes=TEST_DISK_PATH.stat().st_size,
                wipe_method=WIPE_METHOD,
            )

            self.current_job_id = job["id"]
            self.current_job_number = job[
                "job_number"
            ]

            update_wipe_job(
                job_id=self.current_job_id,
                status="RUNNING",
            )

            self.status_label.setText(
                "Secure wipe is running...\n"
                f"Job: {self.current_job_number}"
            )

            QApplication.processEvents()

            result = wipe_test_disk()

            update_wipe_job(
                job_id=self.current_job_id,
                status="WIPE_COMPLETED",
            )

            self.safe_audit(
                action="WIPE_FAKE_TEST_DISK",
                status="SUCCESS",
                details={
                    "job_number": self.current_job_number,
                    "written_bytes": result[
                        "written_bytes"
                    ],
                    "wipe_status": result["status"],
                },
            )

            self.status_label.setText(
                "Secure wipe completed successfully ✅\n"
                f"Job: {self.current_job_number}\n"
                f"Written bytes: {result['written_bytes']}"
            )

        except Exception as error:
            self.safely_update_job(
                status="FAILED",
                verification_status="FAILED",
                error_message=str(error),
                mark_completed=True,
            )

            self.safe_audit(
                action="WIPE_FAKE_TEST_DISK",
                status="FAILED",
                details={
                    "job_number": self.current_job_number,
                    "error": str(error),
                },
            )

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

        if self.current_job_id is None:
            QMessageBox.information(
                self,
                "Wipe Required",
                "Complete secure wipe first.",
            )
            return

        self.verification_passed = False
        self.set_busy(True)

        self.status_label.setText(
            "Verification is running...\n"
            f"Job: {self.current_job_number}"
        )

        QApplication.processEvents()

        try:
            result = verify_test_disk()

            if result["status"] == "passed":
                self.verification_passed = True

                update_wipe_job(
                    job_id=self.current_job_id,
                    status="VERIFIED",
                    verification_status="PASSED",
                )

                self.safe_audit(
                    action="VERIFY_WIPE_RESULT",
                    status="SUCCESS",
                    details={
                        "job_number": (
                            self.current_job_number
                        ),
                        "checked_bytes": result[
                            "checked_bytes"
                        ],
                    },
                )

                self.status_label.setText(
                    "Verification passed successfully ✅\n"
                    f"Job: {self.current_job_number}\n"
                    f"Checked bytes: {result['checked_bytes']}"
                )

            else:
                update_wipe_job(
                    job_id=self.current_job_id,
                    status="FAILED",
                    verification_status="FAILED",
                    error_message=(
                        "Non-zero data found at "
                        f"position {result['failed_position']}"
                    ),
                    mark_completed=True,
                )

                self.safe_audit(
                    action="VERIFY_WIPE_RESULT",
                    status="FAILED",
                    details={
                        "job_number": (
                            self.current_job_number
                        ),
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
            self.safely_update_job(
                status="FAILED",
                verification_status="FAILED",
                error_message=str(error),
                mark_completed=True,
            )

            self.safe_audit(
                action="VERIFY_WIPE_RESULT",
                status="FAILED",
                details={
                    "job_number": self.current_job_number,
                    "error": str(error),
                },
            )

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

        if self.current_job_id is None:
            QMessageBox.information(
                self,
                "Job Missing",
                "No active wipe job was found.",
            )
            return

        self.set_busy(True)

        self.status_label.setText(
            "Generating digitally signed certificate...\n"
            f"Job: {self.current_job_number}"
        )

        QApplication.processEvents()

        try:
            result = generate_certificate(
                device_name=DEVICE_NAME,
                serial_number=SERIAL_NUMBER,
                total_bytes=TEST_DISK_PATH.stat().st_size,
                wipe_method=WIPE_METHOD,
                verification_status="PASSED",
            )

            update_wipe_job(
                job_id=self.current_job_id,
                status="COMPLETED",
                verification_status="PASSED",
                certificate_number=result[
                    "certificate_number"
                ],
                mark_completed=True,
            )

            self.safe_audit(
                action="GENERATE_CERTIFICATE",
                status="SUCCESS",
                details={
                    "job_number": self.current_job_number,
                    "certificate_number": result[
                        "certificate_number"
                    ],
                    "certificate_hash": result[
                        "certificate_hash"
                    ],
                    "signature_algorithm": result[
                        "signature_algorithm"
                    ],
                },
            )

            self.status_label.setText(
                "Signed PDF certificate generated ✅\n"
                f"Job: {self.current_job_number}\n"
                f"Certificate: {result['certificate_number']}"
            )

            QMessageBox.information(
                self,
                "Certificate Created",
                (
                    "Digitally signed certificate created.\n\n"
                    f"PDF: {result['pdf_path']}\n"
                    f"JSON: {result['json_path']}"
                ),
            )

        except Exception as error:
            self.safely_update_job(
                status="CERTIFICATE_FAILED",
                error_message=str(error),
            )

            self.safe_audit(
                action="GENERATE_CERTIFICATE",
                status="FAILED",
                details={
                    "job_number": self.current_job_number,
                    "error": str(error),
                },
            )

            self.status_label.setText(
                "Certificate generation failed ❌\n"
                f"Error: {error}"
            )

        finally:
            self.set_busy(False)

    def check_audit_log(self) -> None:
        self.set_busy(True)

        self.status_label.setText(
            "Verifying audit-log hash chain...\n"
            "Please wait."
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

    def show_wipe_history(self) -> None:
        try:
            jobs = list_wipe_jobs(limit=50)

        except Exception as error:
            QMessageBox.critical(
                self,
                "History Error",
                str(error),
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(
            "DataRakshak Wipe History"
        )
        dialog.resize(1050, 500)

        table = QTableWidget()
        table.setRowCount(len(jobs))
        table.setColumnCount(7)

        table.setHorizontalHeaderLabels(
            [
                "Job Number",
                "Device",
                "Status",
                "Verification",
                "Certificate",
                "Started At",
                "Completed At",
            ]
        )

        for row_number, job in enumerate(jobs):
            values = [
                job.get("job_number"),
                job.get("device_name"),
                job.get("status"),
                job.get("verification_status"),
                job.get("certificate_number"),
                job.get("started_at"),
                job.get("completed_at"),
            ]

            for column_number, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    "" if value is None else str(value)
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

        info_label = QLabel(
            f"Total jobs displayed: {len(jobs)}"
        )

        info_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: white;
            """
        )

        dialog_layout = QVBoxLayout()
        dialog_layout.addWidget(info_label)
        dialog_layout.addWidget(table)

        dialog.setLayout(dialog_layout)
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
                background-color: #0891b2;
                color: white;
                font-weight: bold;
                padding: 7px;
            }
            """
        )

        dialog.exec()

    def verify_certificate_file(self) -> None:
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select DataRakshak Certificate JSON",
            str(Path("certificates").resolve()),
            "Certificate JSON Files (*.json)",
        )

        if not selected_file:
            self.status_label.setText(
                "Certificate verification cancelled."
            )
            return

        self.set_busy(True)

        self.status_label.setText(
            "Verifying certificate hash and signature...\n"
            "Please wait."
        )

        QApplication.processEvents()

        try:
            result = verify_certificate(
                Path(selected_file)
            )

            self.safe_audit(
                action="VERIFY_CERTIFICATE",
                status=result["status"],
                details={
                    "certificate_number": result[
                        "certificate_number"
                    ],
                    "json_path": result["json_path"],
                    "hash_valid": result["hash_valid"],
                    "signature_valid": result[
                        "signature_valid"
                    ],
                },
            )

            if result["status"] == "VALID":
                self.status_label.setText(
                    "Certificate is VALID ✅\n"
                    f"Certificate: {result['certificate_number']}\n"
                    "Hash: Valid | Digital signature: Valid"
                )

                QMessageBox.information(
                    self,
                    "Valid Certificate",
                    (
                        "Certificate verification passed.\n\n"
                        f"Certificate: "
                        f"{result['certificate_number']}\n"
                        f"Device: {result['device_name']}\n"
                        "Hash: Valid\n"
                        "Digital signature: Valid"
                    ),
                )

            else:
                failed_checks = "\n".join(
                    result["failed_checks"]
                )

                self.status_label.setText(
                    "Certificate is TAMPERED ❌\n"
                    f"Certificate: {result['certificate_number']}\n"
                    f"{failed_checks}"
                )

                QMessageBox.critical(
                    self,
                    "Tampered Certificate",
                    (
                        "Certificate verification failed.\n\n"
                        f"{failed_checks}"
                    ),
                )

        except Exception as error:
            self.safe_audit(
                action="VERIFY_CERTIFICATE",
                status="FAILED",
                details={
                    "json_path": selected_file,
                    "error": str(error),
                },
            )

            self.status_label.setText(
                "Certificate verification failed ❌\n"
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