from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
)


class OperationWorker(QObject):
    """Run a long operation without freezing the GUI."""

    progress = Signal(int)
    result = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        operation: Callable[..., Any],
        *args: Any,
        use_progress: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__()

        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        self.use_progress = use_progress

    def report_progress(
        self,
        value: int,
    ) -> None:
        """Emit a safe progress value between 0 and 100."""

        safe_value = max(
            0,
            min(int(value), 100),
        )

        self.progress.emit(
            safe_value
        )

    @Slot()
    def run(self) -> None:
        """Execute the configured operation."""

        operation_kwargs = dict(
            self.kwargs
        )

        if self.use_progress:
            operation_kwargs[
                "progress_callback"
            ] = self.report_progress

        try:
            operation_result = self.operation(
                *self.args,
                **operation_kwargs,
            )

            self.result.emit(
                operation_result
            )

        except Exception as error:
            error_message = (
                f"{type(error).__name__}: {error}"
            )

            self.error.emit(
                error_message
            )

        finally:
            self.finished.emit()


def demo_operation(
    progress_callback: Callable[[int], None],
) -> dict[str, Any]:
    """Run a small worker demonstration."""

    for progress_value in range(
        0,
        101,
        20,
    ):
        progress_callback(
            progress_value
        )

    return {
        "status": "completed",
        "message": (
            "Background worker demonstration completed."
        ),
    }


def main() -> None:
    """Test the worker without opening the main GUI."""

    worker = OperationWorker(
        demo_operation,
        use_progress=True,
    )

    worker.progress.connect(
        lambda value: print(
            f"Progress: {value}%"
        )
    )

    worker.result.connect(
        lambda result: print(
            "Result:",
            result,
        )
    )

    worker.error.connect(
        lambda message: print(
            "Error:",
            message,
        )
    )

    worker.finished.connect(
        lambda: print(
            "Worker finished successfully."
        )
    )

    worker.run()


if __name__ == "__main__":
    main()