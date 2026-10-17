"""سرویس System Tray — pystray + Pillow، مستقل از جزئیات ویجت‌های Tkinter."""
from __future__ import annotations

import logging
import os
import sys
import threading
from enum import Enum
from typing import Callable, Optional

from app.brand import ICON_ASSET, ICON_ICO_ASSET, SITE_DISPLAY_NAME, get_logo_path
from app.paths import get_resource_path

logger = logging.getLogger(__name__)

ScheduleUiFn = Callable[[Callable[[], None]], None]
VoidFn = Callable[[], None]


class TrayStatus(str, Enum):
    READY = "ready"
    EXTRACTING = "extracting"
    UPLOADING = "uploading"
    BATCH = "batch"
    CANCELLING = "cancelling"
    SCHEDULER = "scheduler"
    ERROR = "error"
    HIDDEN = "hidden"


_STATUS_LABELS = {
    TrayStatus.READY: "آماده",
    TrayStatus.EXTRACTING: "در حال استخراج",
    TrayStatus.UPLOADING: "در حال آپلود",
    TrayStatus.BATCH: "استخراج گروهی",
    TrayStatus.CANCELLING: "در حال توقف",
    TrayStatus.SCHEDULER: "زمان‌بندی فعال",
    TrayStatus.ERROR: "خطا",
    TrayStatus.HIDDEN: "در پس‌زمینه",
}


def is_system_tray_supported() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401

        return True
    except ImportError:
        return False


def _load_tray_image():
    from PIL import Image

    candidates = (
        get_resource_path(ICON_ASSET),
        get_resource_path("assets/icon.png"),
        get_logo_path(),
        get_resource_path(ICON_ICO_ASSET),
    )
    for path in candidates:
        if path and os.path.isfile(path):
            try:
                img = Image.open(path)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                # ویندوز Tray معمولاً ۱۶/۳۲ پیکسل — کیفیت بهتر با ۳۲
                return img.resize((32, 32), Image.Resampling.LANCZOS)
            except Exception:
                continue
    # fallback ساده
    return Image.new("RGBA", (32, 32), (37, 99, 235, 255))


class SystemTrayService:
    """آیکن Tray تک‌نسخه‌ای با Callbackهای marshalled به Main Thread."""

    def __init__(
        self,
        *,
        schedule_ui: ScheduleUiFn,
        on_show: VoidFn,
        on_quit: VoidFn,
        on_open_output: VoidFn,
        on_stop_operation: VoidFn,
        on_open_scheduler: VoidFn,
        on_show_status: VoidFn,
        get_status_detail: Optional[Callable[[], str]] = None,
    ) -> None:
        self._schedule_ui = schedule_ui
        self._on_show = on_show
        self._on_quit = on_quit
        self._on_open_output = on_open_output
        self._on_stop_operation = on_stop_operation
        self._on_open_scheduler = on_open_scheduler
        self._on_show_status = on_show_status
        self._get_status_detail = get_status_detail

        self._lock = threading.RLock()
        self._status = TrayStatus.READY
        self._detail = ""
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._stopping = False
        self._available = is_system_tray_supported()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def is_running(self) -> bool:
        with self._lock:
            return bool(self._started and self._icon is not None and not self._stopping)

    def start(self) -> bool:
        if not self._available:
            return False
        with self._lock:
            if self._started or self._stopping:
                return self._icon is not None
            if self._thread is not None and self._thread.is_alive():
                return True
            self._started = True
            self._stopping = False
            self._thread = threading.Thread(
                target=self._run_icon_loop,
                name="SystemTrayService",
                daemon=True,
            )
            self._thread.start()
        return True

    def stop(self, timeout: float = 4.0) -> None:
        with self._lock:
            self._stopping = True
            icon = self._icon
            self._started = False
        if icon is not None:
            try:
                icon.stop()
            except Exception as exc:
                logger.debug("tray stop: %s", exc)
        thread = self._thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        with self._lock:
            self._icon = None
            self._thread = None

    def set_status(self, status: TrayStatus, detail: str = "") -> None:
        with self._lock:
            self._status = status
            self._detail = (detail or "").strip()
            tooltip = self._build_tooltip_locked()
            icon = self._icon
        if icon is not None:
            try:
                icon.title = tooltip
            except Exception:
                pass
            try:
                icon.update_menu()
            except Exception:
                pass

    def status_label(self) -> str:
        with self._lock:
            return self._build_status_line_locked()

    def _build_tooltip_locked(self) -> str:
        line = self._build_status_line_locked()
        return f"{SITE_DISPLAY_NAME} — {line}"

    def _build_status_line_locked(self) -> str:
        label = _STATUS_LABELS.get(self._status, "آماده")
        if self._detail:
            return f"{label} · {self._detail[:80]}"
        return label

    def _run_icon_loop(self) -> None:
        try:
            import pystray
            from pystray import MenuItem as item
        except ImportError:
            with self._lock:
                self._started = False
                self._available = False
            return

        try:
            image = _load_tray_image()
        except Exception as exc:
            logger.warning("tray icon image failed: %s", exc)
            with self._lock:
                self._started = False
            return

        def ui(fn: VoidFn):
            def _handler(icon=None, item=None):  # noqa: ARG001
                try:
                    self._schedule_ui(fn)
                except Exception as exc:
                    logger.debug("tray marshal failed: %s", exc)

            return _handler

        def status_text(_item=None) -> str:
            if self._get_status_detail:
                try:
                    extra = self._get_status_detail() or ""
                    if extra:
                        return f"وضعیت: {extra}"
                except Exception:
                    pass
            with self._lock:
                return f"وضعیت: {self._build_status_line_locked()}"

        menu = pystray.Menu(
            item("باز کردن برنامه", ui(self._on_show), default=True),
            item(status_text, ui(self._on_show_status)),
            pystray.Menu.SEPARATOR,
            item("باز کردن پوشه خروجی", ui(self._on_open_output)),
            item("توقف عملیات جاری", ui(self._on_stop_operation)),
            item("زمان‌بندی‌ها", ui(self._on_open_scheduler)),
            pystray.Menu.SEPARATOR,
            item("خروج کامل", ui(self._on_quit)),
        )

        icon = pystray.Icon(
            name="divar_extractor_tray",
            icon=image,
            title=f"{SITE_DISPLAY_NAME} — آماده",
            menu=menu,
        )
        with self._lock:
            if self._stopping:
                return
            self._icon = icon
            icon.title = self._build_tooltip_locked()

        try:
            icon.run()
        except Exception as exc:
            logger.warning("tray icon run failed: %s", exc)
        finally:
            with self._lock:
                self._icon = None
                self._started = False
