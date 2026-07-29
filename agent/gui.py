from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import (
    Qt,
    QThread,
)
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from agent.paths import (
    CERTIFICATES_DIR,
    TEST_DISK_PATH,
    ensure_runtime_directories,
)
from agent.services.audit_logger import (
    verify_audit_log,
    write_audit_log,
)
from agent.services.certificate_service import (
    generate_certificate,
)
from agent.services.certificate_verifier import (
    verify_certificate,
)
from agent.services.database_service import (
    create_wipe_job,
    initialize_database,
    list_wipe_jobs,
    update_wipe_job,
)
from agent.services.operation_worker import (
    OperationWorker,
)
from agent.services.verifier import (
    verify_test_disk,
)
from agent.services.wipe_engine import (
    wipe_test_disk,
)


TEST_DISK_SIZE = 10 * 1024 * 1024

DEVICE_NAME = "Fake Test Disk"
SERIAL_NUMBER = "TEST-DISK-0001"
WIPE_METHOD = "Single-pass zero overwrite"


class DataRakshakWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        ensure_runtime_directories()
        initialize_database()

        self.verification_passed = False

        self.current_job_id: int | None = None
        self.current_job_number: str | None = None

        self.operation_thread: QThread | None = None
        self.operation_worker: OperationWorker | None = None
        self.active_operation: str | None = None

        self.setWindowTitle("DataRakshak")
        self.resize(820, 960)

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
        self.status_label.setMinimumHeight(125)
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

        self.progress_label = QLabel(
            "Operation Progress"
        )
        self.progress_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.progress_label.setStyleSheet(
            """
            font-size: 14px;
            font-weight: bold;
            color: white;
            background: transparent;
            """
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setMinimumHeight(32)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #334155;
                border-radius: 8px;
                background-color: #1e293b;
                color: white;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #14b8a6;
                border-radius: 6px;
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
        layout.setContentsMargins(
            75,
            32,
            75,
            32,
        )
        layout.setSpacing(12)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(12)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.create_disk_button)
        layout.addWidget(self.wipe_button)
        layout.addWidget(self.verify_button)
        layout.addWidget(self.certificate_button)
        layout.addWidget(self.audit_button)
        layout.addWidget(self.history_button)
        layout.addWidget(
            self.certificate_verify_button
        )

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

        button.setMinimumHeight(48)

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
                background-color: #64748b;
                color: #cbd5e1;
            }}
            """
        )

        return button

    def is_operation_running(self) -> bool:
        return (
            self.operation_thread is not None
            and self.operation_thread.isRunning()
        )

    def set_busy(
        self,
        busy: bool,
    ) -> None:
        enabled = not busy

        self.create_disk_button.setEnabled(enabled)
        self.wipe_button.setEnabled(enabled)
        self.verify_button.setEnabled(enabled)
        self.audit_button.setEnabled(enabled)
        self.history_button.setEnabled(enabled)

        self.certificate_verify_button.setEnabled(
            enabled
        )

        if busy:
            self.certificate_button.setEnabled(False)
        else:
            self.certificate_button.setEnabled(
                self.verification_passed
            )

    def reset_progress(
        self,
        label: str = "Operation Progress",
    ) -> None:
        self.progress_label.setText(label)
        self.progress_bar.setValue(0)

    def update_wipe_progress(
        self,
        progress: int,
    ) -> None:
        safe_progress = max(
            0,
            min(progress, 100),
        )

        self.progress_label.setText(
            "Secure Wipe Progress"
        )

        self.progress_bar.setValue(
            safe_progress
        )

        self.status_label.setText(
            "Secure wipe is running...\n"
            f"Job: {self.current_job_number}\n"
            f"Progress: {safe_progress}%"
        )

    def update_verification_progress(
        self,
        progress: int,
    ) -> None:
        safe_progress = max(
            0,
            min(progress, 100),
        )

        self.progress_label.setText(
            "Verification Progress"
        )

        self.progress_bar.setValue(
            safe_progress
        )

        self.status_label.setText(
            "Verification is running...\n"
            f"Job: {self.current_job_number}\n"
            f"Progress: {safe_progress}%"
        )

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

    def start_background_operation(
        self,
        operation_name: str,
        operation: Callable[..., Any],
        progress_handler: Callable[[int], None],
    ) -> None:
        if self.is_operation_running():
            QMessageBox.information(
                self,
                "Operation Running",
                "Another operation is already running.",
            )
            return

        thread = QThread(self)

        worker = OperationWorker(
            operation,
            use_progress=True,
        )

        worker.moveToThread(thread)

        thread.started.connect(
            worker.run
        )

        worker.progress.connect(
            progress_handler
        )

        worker.result.connect(
            lambda result, name=operation_name: (
                self.handle_background_result(
                    name,
                    result,
                )
            )
        )

        worker.error.connect(
            lambda message, name=operation_name: (
                self.handle_background_error(
                    name,
                    message,
                )
            )
        )

        worker.finished.connect(
            thread.quit
        )

        worker.finished.connect(
            worker.deleteLater
        )

        thread.finished.connect(
            thread.deleteLater
        )

        thread.finished.connect(
            self.background_thread_finished
        )

        self.operation_thread = thread
        self.operation_worker = worker
        self.active_operation = operation_name

        self.set_busy(True)

        thread.start()

    def handle_background_result(
        self,
        operation_name: str,
        result: object,
    ) -> None:
        if not isinstance(result, dict):
            self.handle_background_error(
                operation_name,
                "The operation returned an invalid result.",
            )
            return

        if operation_name == "WIPE":
            self.handle_wipe_result(result)

        elif operation_name == "VERIFY":
            self.handle_verification_result(result)

    def handle_background_error(
        self,
        operation_name: str,
        error_message: str,
    ) -> None:
        if operation_name == "WIPE":
            self.safely_update_job(
                status="FAILED",
                verification_status="FAILED",
                error_message=error_message,
                mark_completed=True,
            )

            self.safe_audit(
                action="WIPE_FAKE_TEST_DISK",
                status="FAILED",
                details={
                    "job_number": (
                        self.current_job_number
                    ),
                    "error": error_message,
                },
            )

            self.status_label.setText(
                "Secure wipe failed ❌\n"
                f"Error: {error_message}"
            )

        elif operation_name == "VERIFY":
            self.verification_passed = False

            self.safely_update_job(
                status="FAILED",
                verification_status="FAILED",
                error_message=error_message,
                mark_completed=True,
            )

            self.safe_audit(
                action="VERIFY_WIPE_RESULT",
                status="FAILED",
                details={
                    "job_number": (
                        self.current_job_number
                    ),
                    "error": error_message,
                },
            )

            self.status_label.setText(
                "Verification failed ❌\n"
                f"Error: {error_message}"
            )

    def background_thread_finished(self) -> None:
        self.operation_thread = None
        self.operation_worker = None
        self.active_operation = None

        self.set_busy(False)

    def create_fake_test_disk(self) -> None:
        if self.is_operation_running():
            return

        self.verification_passed = False
        self.current_job_id = None
        self.current_job_number = None

        self.reset_progress(
            "Fake Disk Creation"
        )

        self.set_busy(True)

        self.status_label.setText(
            "Creating fake test disk...\n"
            "Please wait."
        )

        QApplication.processEvents()

        try:
            ensure_runtime_directories()

            TEST_DISK_PATH.write_bytes(
                b"A" * TEST_DISK_SIZE
            )

            disk_size = (
                TEST_DISK_PATH.stat().st_size
            )

            self.progress_bar.setValue(100)

            self.safe_audit(
                action="CREATE_FAKE_TEST_DISK",
                status="SUCCESS",
                details={
                    "path": str(TEST_DISK_PATH),
                    "size_bytes": disk_size,
                },
            )

            self.status_label.setText(
                "Fake test disk created successfully ✅\n"
                f"Location: {TEST_DISK_PATH}\n"
                f"Size: {disk_size} bytes"
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
        if self.is_operation_running():
            QMessageBox.information(
                self,
                "Operation Running",
                "Wait for the current operation to finish.",
            )
            return

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

        if (
            confirmation
            != QMessageBox.StandardButton.Yes
        ):
            self.safe_audit(
                action="WIPE_FAKE_TEST_DISK",
                status="CANCELLED",
                details={
                    "reason": (
                        "User cancelled operation"
                    ),
                },
            )

            self.status_label.setText(
                "Secure wipe cancelled by user."
            )
            return

        self.verification_passed = False

        self.reset_progress(
            "Secure Wipe Progress"
        )

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
                total_bytes=(
                    TEST_DISK_PATH.stat().st_size
                ),
                wipe_method=WIPE_METHOD,
            )

            self.current_job_id = int(
                job["id"]
            )

            self.current_job_number = str(
                job["job_number"]
            )

            update_wipe_job(
                job_id=self.current_job_id,
                status="RUNNING",
            )

            self.status_label.setText(
                "Secure wipe is starting...\n"
                f"Job: {self.current_job_number}"
            )

            self.start_background_operation(
                operation_name="WIPE",
                operation=wipe_test_disk,
                progress_handler=(
                    self.update_wipe_progress
                ),
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
                    "job_number": (
                        self.current_job_number
                    ),
                    "error": str(error),
                },
            )

            self.status_label.setText(
                "Secure wipe could not start ❌\n"
                f"Error: {error}"
            )

            self.set_busy(False)

    def handle_wipe_result(
        self,
        result: dict[str, Any],
    ) -> None:
        self.progress_bar.setValue(100)

        self.safely_update_job(
            status="WIPE_COMPLETED",
        )

        self.safe_audit(
            action="WIPE_FAKE_TEST_DISK",
            status="SUCCESS",
            details={
                "job_number": (
                    self.current_job_number
                ),
                "written_bytes": result.get(
                    "written_bytes"
                ),
                "wipe_status": result.get(
                    "status"
                ),
                "final_progress": result.get(
                    "final_progress"
                ),
            },
        )

        self.status_label.setText(
            "Secure wipe completed successfully ✅\n"
            f"Job: {self.current_job_number}\n"
            f"Written bytes: {result.get('written_bytes')}"
        )

    def start_verification(self) -> None:
        if self.is_operation_running():
            QMessageBox.information(
                self,
                "Operation Running",
                "Wait for the current operation to finish.",
            )
            return

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

        self.reset_progress(
            "Verification Progress"
        )

        self.status_label.setText(
            "Verification is starting...\n"
            f"Job: {self.current_job_number}"
        )

        self.start_background_operation(
            operation_name="VERIFY",
            operation=verify_test_disk,
            progress_handler=(
                self.update_verification_progress
            ),
        )

    def handle_verification_result(
        self,
        result: dict[str, Any],
    ) -> None:
        if result.get("status") == "passed":
            self.verification_passed = True

            self.progress_bar.setValue(100)

            self.safely_update_job(
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
                    "checked_bytes": result.get(
                        "checked_bytes"
                    ),
                    "final_progress": result.get(
                        "final_progress"
                    ),
                },
            )

            self.status_label.setText(
                "Verification passed successfully ✅\n"
                f"Job: {self.current_job_number}\n"
                f"Checked bytes: {result.get('checked_bytes')}"
            )

            return

        self.verification_passed = False

        failed_position = result.get(
            "failed_position"
        )

        self.progress_bar.setValue(
            int(
                result.get(
                    "final_progress",
                    0,
                )
            )
        )

        self.safely_update_job(
            status="FAILED",
            verification_status="FAILED",
            error_message=(
                "Non-zero data found at "
                f"position {failed_position}"
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
                "failed_position": failed_position,
                "checked_bytes": result.get(
                    "checked_bytes"
                ),
            },
        )

        self.status_label.setText(
            "Verification failed ❌\n"
            "Non-zero data was found.\n"
            f"Position: {failed_position}"
        )

    def create_certificate(self) -> None:
        if self.is_operation_running():
            return

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

        self.reset_progress(
            "Certificate Generation"
        )

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
                total_bytes=(
                    TEST_DISK_PATH.stat().st_size
                ),
                wipe_method=WIPE_METHOD,
                verification_status="PASSED",
            )

            self.progress_bar.setValue(100)

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
                    "job_number": (
                        self.current_job_number
                    ),
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
                    "job_number": (
                        self.current_job_number
                    ),
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
        if self.is_operation_running():
            return

        self.reset_progress(
            "Audit Log Verification"
        )

        self.set_busy(True)

        self.status_label.setText(
            "Verifying audit-log hash chain...\n"
            "Please wait."
        )

        QApplication.processEvents()

        try:
            result = verify_audit_log()

            self.progress_bar.setValue(100)

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
        if self.is_operation_running():
            return

        try:
            jobs = list_wipe_jobs(
                limit=50
            )

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

        dialog.resize(
            1050,
            500,
        )

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
        if self.is_operation_running():
            return

        selected_file, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Select DataRakshak Certificate JSON",
                str(CERTIFICATES_DIR),
                "Certificate JSON Files (*.json)",
            )
        )

        if not selected_file:
            self.status_label.setText(
                "Certificate verification cancelled."
            )
            return

        self.reset_progress(
            "Certificate Verification"
        )

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

            self.progress_bar.setValue(100)

            self.safe_audit(
                action="VERIFY_CERTIFICATE",
                status=result["status"],
                details={
                    "certificate_number": result[
                        "certificate_number"
                    ],
                    "json_path": result["json_path"],
                    "hash_valid": result[
                        "hash_valid"
                    ],
                    "signature_valid": result[
                        "signature_valid"
                    ],
                    "fingerprint_valid": result[
                        "fingerprint_valid"
                    ],
                },
            )

            if result["status"] == "VALID":
                self.status_label.setText(
                    "Certificate is VALID ✅\n"
                    f"Certificate: {result['certificate_number']}\n"
                    "Hash and digital signature are valid."
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
                        "Digital signature: Valid\n"
                        "Public-key fingerprint: Valid"
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

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        if self.is_operation_running():
            QMessageBox.warning(
                self,
                "Operation Running",
                (
                    "A wipe or verification operation is running.\n\n"
                    "Wait for it to finish before closing "
                    "DataRakshak."
                ),
            )

            event.ignore()
            return

        event.accept()


def start_application() -> None:
    app = QApplication(sys.argv)

    window = DataRakshakWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    start_application()