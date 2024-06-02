from typing import Callable

from PyQt6.QtCore import QRunnable, QObject, pyqtSignal


class WorkerSignals(QObject):
    result = pyqtSignal(object)


class Worker(QRunnable):
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        self.signals.result.emit(self._fn(*self._args, **self._kwargs))

