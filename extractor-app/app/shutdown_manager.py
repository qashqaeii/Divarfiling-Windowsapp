"""مدیریت خروج کنترل‌شده — توقف عملیات، Scheduler، Tray و منابع."""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

VoidFn = Callable[[], None]
BoolFn = Callable[[], bool]


class ShutdownManager:
    """خروج Production-Ready بدون باقی‌ماندن Process/Thread معلق."""

    def __init__(
        self,
        *,
        schedule_ui: Callable[[int, Callable[[], None]], None],
        is_busy: BoolFn,
        request_cancel: VoidFn,
        stop_scheduler: VoidFn,
        stop_tray: VoidFn,
        save_state: VoidFn,
        destroy_app: VoidFn,
        join_worker: Callable[[float], bool],
        on_progress: Optional[Callable[[str], None]] = None,
        cancel_wait_seconds: float = 8.0,
        force_after_seconds: float = 12.0,
    ) -> None:
        self._schedule_ui = schedule_ui
        self._is_busy = is_busy
        self._request_cancel = request_cancel
        self._stop_scheduler = stop_scheduler
        self._stop_tray = stop_tray
        self._save_state = save_state
        self._destroy_app = destroy_app
        self._join_worker = join_worker
        self._on_progress = on_progress
        self._cancel_wait_seconds = cancel_wait_seconds
        self._force_after_seconds = force_after_seconds

        self._lock = threading.Lock()
        self._shutting_down = False
        self._finalize_scheduled = False

    @property
    def is_shutting_down(self) -> bool:
        with self._lock:
            return self._shutting_down

    def request_shutdown(self, *, reason: str = "user") -> None:
        with self._lock:
            if self._shutting_down:
                return
            self._shutting_down = True

        logger.info("shutdown requested (%s)", reason)
        self._emit("در حال خروج کامل…")

        try:
            self._stop_scheduler()
        except Exception as exc:
            logger.debug("stop scheduler: %s", exc)

        busy = False
        try:
            busy = bool(self._is_busy())
        except Exception:
            busy = False

        if busy:
            try:
                self._request_cancel()
            except Exception as exc:
                logger.debug("request cancel: %s", exc)
            self._emit("توقف عملیات جاری قبل از خروج…")
            threading.Thread(
                target=self._wait_then_finalize,
                name="ShutdownWait",
                daemon=True,
            ).start()
            # ایمنی: اگر join طول کشید، اجباراً ببند
            self._schedule_ui(
                int(self._force_after_seconds * 1000),
                lambda: self._finalize(force=True),
            )
        else:
            self._finalize(force=False)

    def _wait_then_finalize(self) -> None:
        deadline = time.time() + self._cancel_wait_seconds
        while time.time() < deadline:
            try:
                if not self._is_busy():
                    break
            except Exception:
                break
            # منتظر اتمام همکاری‌جویانه worker
            if self._join_worker(0.35):
                break
        self._schedule_ui(0, lambda: self._finalize(force=False))

    def _finalize(self, *, force: bool) -> None:
        with self._lock:
            if self._finalize_scheduled and not force:
                return
            self._finalize_scheduled = True
            self._shutting_down = True

        self._emit("آزادسازی منابع…")
        try:
            self._save_state()
        except Exception as exc:
            logger.debug("save state on shutdown: %s", exc)

        try:
            self._stop_tray()
        except Exception as exc:
            logger.debug("stop tray on shutdown: %s", exc)

        # فرصت کوتاه برای توقف thread آیکن
        try:
            self._join_worker(0.5)
        except Exception:
            pass

        try:
            self._destroy_app()
        except Exception as exc:
            logger.warning("destroy app failed: %s", exc)

    def _emit(self, message: str) -> None:
        if not self._on_progress:
            return
        try:
            self._on_progress(message)
        except Exception:
            pass
