from PySide6.QtCore import QThread, Signal


class Cancelled(Exception):
    pass


class Job(QThread):
    """Run a cancellable operation and deliver results to the UI thread."""

    progress = Signal(object, str)
    result = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.operation = operation

    def check_cancel(self):
        if self.isInterruptionRequested():
            raise Cancelled()

    def run(self):
        try:
            result = self.operation(self.progress.emit, self.check_cancel)
            self.check_cancel()
        except Cancelled:
            self.cancelled.emit()
        except Exception as error:
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                self.failed.emit(str(error) or type(error).__name__)
        else:
            self.result.emit(result)
