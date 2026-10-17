"""مدیریت متمرکز وضعیت اجرای استخراج — single / batch / scheduler."""
from __future__ import annotations

import threading
from enum import Enum


class ExecutionState(str, Enum):
    IDLE = "idle"
    RUNNING_SINGLE = "running_single"
    RUNNING_BATCH = "running_batch"
    CANCELLING = "cancelling"


class ExecutionStateManager:
    """فقط یک عملیات استخراج در هر لحظه — شروع فقط از IDLE."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = ExecutionState.IDLE

    @property
    def state(self) -> ExecutionState:
        with self._lock:
            return self._state

    @property
    def is_idle(self) -> bool:
        return self.state == ExecutionState.IDLE

    @property
    def is_running(self) -> bool:
        return self.state in (
            ExecutionState.RUNNING_SINGLE,
            ExecutionState.RUNNING_BATCH,
            ExecutionState.CANCELLING,
        )

    def try_start(self, target: ExecutionState) -> bool:
        if target not in (ExecutionState.RUNNING_SINGLE, ExecutionState.RUNNING_BATCH):
            return False
        with self._lock:
            if self._state != ExecutionState.IDLE:
                return False
            self._state = target
            return True

    def request_cancel(self) -> bool:
        with self._lock:
            if self._state in (
                ExecutionState.RUNNING_SINGLE,
                ExecutionState.RUNNING_BATCH,
            ):
                self._state = ExecutionState.CANCELLING
                return True
            return False

    def finish(self) -> None:
        with self._lock:
            self._state = ExecutionState.IDLE
