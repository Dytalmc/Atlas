"""Keep Gemini work away from the PyQt UI thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


class TaskWorker(QObject):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, task: Callable[[], Any]) -> None:
        super().__init__()
        self._task = task

    @pyqtSlot()
    def run(self) -> None:
        try:
            self.completed.emit(self._task())
        except Exception as error:  # UI needs a human-readable error, not a crashed event loop.
            self.failed.emit(str(error) or error.__class__.__name__)
        finally:
            self.finished.emit()


class _TaskCallbacks(QObject):
    """Receives worker signals on the GUI thread before touching widgets."""

    def __init__(
        self,
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None],
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        self._on_success = on_success
        self._on_error = on_error

    @pyqtSlot(object)
    def successful(self, value: Any) -> None:
        self._on_success(value)

    @pyqtSlot(str)
    def unsuccessful(self, message: str) -> None:
        self._on_error(message)


class TaskRunner(QObject):
    """Owns short-lived worker threads until their work is finished."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._threads: list[QThread] = []
        self._workers: dict[QThread, TaskWorker] = {}
        self._callbacks: dict[QThread, _TaskCallbacks] = {}

    def run(
        self,
        task: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None],
    ) -> None:
        thread = QThread(self)
        worker = TaskWorker(task)
        callbacks = _TaskCallbacks(on_success, on_error, self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(callbacks.successful)
        worker.failed.connect(callbacks.unsuccessful)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._discard(thread))
        self._threads.append(thread)
        # `moveToThread` changes QObject affinity, not Python ownership. Keep a
        # Python reference until the thread has actually finished.
        self._workers[thread] = worker
        self._callbacks[thread] = callbacks
        thread.start()

    def _discard(self, thread: QThread) -> None:
        if thread in self._threads:
            self._threads.remove(thread)
        self._workers.pop(thread, None)
        callbacks = self._callbacks.pop(thread, None)
        if callbacks is not None:
            callbacks.deleteLater()
