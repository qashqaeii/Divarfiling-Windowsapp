"""رابط کاربری اپ استخراج — CustomTkinter RTL."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser
import json
from tkinter import messagebox
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from app.brand import (
    CREATOR_NAME,
    CREATOR_PHONE,
    CREATOR_PHONE_DISPLAY,
    CREATOR_TELEGRAM,
    CREATOR_TELEGRAM_URL,
    DEFAULT_BUY_LICENSE_URL,
    DEFAULT_LICENSE_API_URL,
    DEFAULT_PLATFORM_UPLOAD_URL,
    ICON_ICO_ASSET,
    LOGO_ASSET,
    SITE_DISPLAY_NAME,
    SITE_URL,
    SITE_URL_DISPLAY,
    SUPPORT_EMAIL,
    get_logo_path,
)
from app.constants import TRANSACTION_TYPES, MAX_EXTRACTION_ITEMS, SCHEDULER_MAX_ITEMS
from app.execution_state import ExecutionState, ExecutionStateManager
from app.extraction_engine import ExtractionEngine
from app.extraction_job import ExtractionJobService
from app.batch_runner import BatchExtractionRunner
from app.batch_models import BatchJobResult, BatchJobSpec, BatchRunSummary, JobStatus, UploadStatus
from app.category_jobs import build_job_settings, resolve_api_slug
from app.filter_utils import (
    format_filter_int,
    is_rent_transaction,
    normalize_saved_filters,
    resolve_search_category,
    supported_amenities_for_category,
)
from app.formatters import fa_digits, format_datetime_fa, format_duration_fa, format_expiry_fa, format_timestamp_fa
from app.desktop_auth_client import DesktopAuthClient, DesktopAuthError
from app.license_client import LicenseClient
from app.notifications import WindowsNotificationService, default_notification_settings
from app.paths import get_app_root, get_output_dir, get_resource_path
from app.places import PlacesManager
from app.scheduler import (
    ExtractionScheduler,
    SCHEDULER_BATCH_MIN_HOURS,
    clamp_interval_for_mode,
    default_scheduler_config,
    hours_to_interval_label,
    interval_label_to_hours,
    scheduler_interval_labels,
)
from app.shutdown_manager import ShutdownManager
from app.storage import get_storage
from app.system_tray import SystemTrayService, TrayStatus, is_system_tray_supported
from app.theme import (
    COLORS,
    LOG_LEVEL_BADGES,
    SPACE_SM,
    setup_theme,
)
from app.tray_settings import default_tray_settings, parse_tray_prefs
from app.ui.tokens import APP_VERSION
from app.ui.components import (
    AppCanvas,
    AppHeader,
    styled_entry,
    apply_combobox_rtl,
)
from app.ui.components.status_bar import AppStatusBar
from app.ui.components.toast import Toast
from app.ui.components.account_login_panel import (
    set_account_login_busy,
    set_account_login_error,
    set_account_login_fields,
    set_account_session_visible,
)
from app.ui.components.license_selection_dialog import LicenseSelectionDialog
from app.ui.components.license_account_panel import update_license_account_panel
from app.ui.components.tray_close_dialog import CloseToTrayDialog
from app.ui.pages import (
    build_about_page,
    build_extraction_page,
    build_license_page,
    build_output_page,
    build_schedule_page,
    build_settings_page,
    update_summary_chips,
)
from app.ui.tokens import MIN_WINDOW_H, MIN_WINDOW_W, SPACE_MD, SPACE_XS
from app.widgets import enable_entry_shortcuts, enable_textbox_shortcuts, set_readonly_entry_value

from app.ui.components.batch_dialogs import BatchConfirmDialog, BatchReportDialog
import export_divar_items as scraper


class ExtractorApp(ctk.CTk):
    PLATFORM_UPLOAD_URL = os.environ.get(
        "EXTRACTOR_PLATFORM_URL", DEFAULT_PLATFORM_UPLOAD_URL
    )

    def __init__(self) -> None:
        setup_theme()
        super().__init__()
        self.title(f"{SITE_DISPLAY_NAME} · استخراج حرفه‌ای")
        self.minsize(MIN_WINDOW_W, MIN_WINDOW_H)
        self.configure(fg_color=COLORS["app_bg"])

        self._brand_images: Dict[str, ctk.CTkImage] = {}
        self._set_window_icon()

        self._storage = get_storage()
        self._settings = self._storage.load_settings()
        if "notifications" not in self._settings:
            self._settings["notifications"] = default_notification_settings()
        if "tray" not in self._settings:
            self._settings["tray"] = default_tray_settings()
        api_url = DEFAULT_LICENSE_API_URL.rstrip("/")
        self._license = LicenseClient(api_base_url=api_url)
        self._desktop_auth = DesktopAuthClient(api_base_url=api_url)
        self.license_validated = False

        self._cancel_event = threading.Event()
        self._queue: queue.Queue = queue.Queue()
        self._ui_callbacks: queue.Queue = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._execution = ExecutionStateManager()
        self._batch_summary: Optional[BatchRunSummary] = None
        self._batch_base_settings: Optional[Dict[str, Any]] = None
        self._batch_job_index = 0
        self._batch_job_total = 0
        self._active_batch_run = False
        self._last_output_path: Optional[str] = None
        self._last_run_settings: Optional[Dict[str, Any]] = None
        self.scrape_start_time: Optional[float] = None
        self._hidden_to_tray = False
        self._close_hint_dialog: Optional[Any] = None
        self._tray: Optional[SystemTrayService] = None
        self._shutdown: Optional[ShutdownManager] = None
        self._tray_status_poll_id: Optional[str] = None

        ext_saved = self._settings.get("extraction") or {}
        self.output_format = ctk.StringVar(
            value=ext_saved.get("output_format")
            or self._settings.get("output_format", "excel"),
        )
        self.output_format.trace_add("write", lambda *_: self._update_path_preview())
        self._upload_platform_var = ctk.BooleanVar(
            value=bool(ext_saved.get("upload_to_platform", True)),
        )
        self._upload_platform_var.trace_add("write", lambda *_: self._update_batch_summary())
        self._advertiser_filter = ctk.StringVar(value="all")
        self._scheduler_running = False
        self._run_is_scheduled = False
        self._run_had_output = False
        self._run_cancelled = False
        self._last_scrape_error = ""
        self._pending_output_path: Optional[str] = None
        self._last_run_stats: Dict[str, int] = {"total": 0, "done": 0, "ok": 0}
        self._extraction_mode = "single"

        self._places = PlacesManager(on_log=self._emit_threadsafe)
        self._engine = ExtractionEngine(
            scraper,
            self._places,
            self._storage,
            on_log=self._emit_threadsafe,
            on_progress=self._progress_threadsafe,
            is_cancelled=self._cancel_event.is_set,
        )
        self._job_service = ExtractionJobService(
            self._engine,
            self._license,
            self._places,
            on_log=self._emit_threadsafe,
            is_cancelled=self._cancel_event.is_set,
        )
        self._batch_runner = BatchExtractionRunner(
            self._job_service,
            self._storage,
            on_log=self._emit_threadsafe,
            on_progress=self._batch_progress_threadsafe,
            is_cancelled=self._cancel_event.is_set,
            on_job_complete=self._batch_job_complete_threadsafe,
        )

        self._build_ui()
        self._notifier = WindowsNotificationService(
            get_settings=lambda: self._settings,
            is_app_minimized=self._is_app_minimized,
            fallback_toast=self._notification_fallback,
        )
        self._scheduler = ExtractionScheduler(
            self,
            on_run=self._scheduler_fire,
            on_status=self._scheduler_status_update,
        )
        self._init_tray_and_shutdown()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(0, self._apply_startup_window)
        self._poll_queue()
        self.after(50, self._startup)

    def _brand_logo_image(self, size: int) -> Optional[ctk.CTkImage]:
        key = f"logo_{size}"
        if key in self._brand_images:
            return self._brand_images[key]
        logo_path = get_logo_path()
        if not os.path.isfile(logo_path):
            logo_path = get_resource_path(LOGO_ASSET)
        if not os.path.isfile(logo_path):
            logo_path = get_resource_path("assets/icon.png")
        if not os.path.isfile(logo_path):
            return None
        try:
            from PIL import Image

            img = Image.open(logo_path)
            image = ctk.CTkImage(img, img, size=(size, size))
            self._brand_images[key] = image
            return image
        except Exception:
            return None

    def _is_app_minimized(self) -> bool:
        try:
            if self._hidden_to_tray:
                return True
            state = str(self.state())
            if state == "iconic":
                return True
            # withdrawn از Taskbar هم «مخفی» محسوب می‌شود
            if not bool(self.winfo_viewable()):
                return True
            return False
        except Exception:
            return bool(getattr(self, "_hidden_to_tray", False))

    def _notification_fallback(self, message: str, tone: str) -> None:
        first_line = (message or "").split("\n", 1)[0].strip()
        if not first_line:
            return
        safe_tone = tone if tone in ("success", "error", "warning", "info") else "info"
        try:
            self.after(0, lambda: Toast.show(self, first_line, tone=safe_tone))
        except Exception:
            pass

    def _collect_notification_settings(self) -> Dict[str, Any]:
        cfg = dict(default_notification_settings())
        if hasattr(self, "_notify_enabled_var"):
            cfg.update({
                "enabled": bool(self._notify_enabled_var.get()),
                "sound": bool(self._notify_sound_var.get()),
                "when_minimized_only": bool(self._notify_minimized_var.get()),
                "extraction": bool(self._notify_extraction_var.get()),
                "scheduler": bool(self._notify_scheduler_var.get()),
                "license": bool(self._notify_license_var.get()),
                "errors": bool(self._notify_errors_var.get()),
                "upload": bool(self._notify_upload_var.get()),
            })
        else:
            cfg.update(self._settings.get("notifications") or {})
        return cfg

    def _collect_tray_settings(self) -> Dict[str, Any]:
        cfg = dict(default_tray_settings())
        cfg.update(self._settings.get("tray") or {})
        if hasattr(self, "_tray_close_to_tray_var"):
            cfg["close_to_tray"] = bool(self._tray_close_to_tray_var.get())
        if hasattr(self, "_notify_extraction_var"):
            cfg["notify_extraction_complete"] = bool(self._notify_extraction_var.get())
        if hasattr(self, "_notify_errors_var"):
            cfg["notify_errors"] = bool(self._notify_errors_var.get())
        return cfg

    def _test_windows_notification(self) -> None:
        sent = self._notifier.test()
        if sent:
            self._set_status_message("اعلان تست ارسال شد", tone="success")
        else:
            Toast.show(
                self,
                "اعلان ویندوز ارسال نشد — تنظیمات یا Focus Assist را بررسی کنید.",
                tone="warning",
            )

    def _reset_run_tracking(self, *, scheduled: bool) -> None:
        self._run_is_scheduled = scheduled
        self._run_had_output = False
        self._run_cancelled = False
        self._last_scrape_error = ""
        self._pending_output_path = None
        self._last_run_stats = {"total": 0, "done": 0, "ok": 0}

    def _notify_extraction_complete(self) -> None:
        duration_text = ""
        duration_seconds = 0
        if self.scrape_start_time:
            duration_seconds = int(time.time() - self.scrape_start_time)
            mins, secs = divmod(duration_seconds, 60)
            duration_text = f"{fa_digits(mins)}:{fa_digits(f'{secs:02d}')}"

        stats = self._last_run_stats or {}
        ok_count = int(stats.get("ok") or 0)
        total_count = int(stats.get("total") or 0)

        settings = self._last_run_settings or {}
        city = str(settings.get("city") or "")
        output_path = self._pending_output_path or self._last_output_path or ""

        if self._run_cancelled:
            status = "cancelled"
            self._notifier.extraction_cancelled(scheduled=self._run_is_scheduled)
        elif self._run_had_output and output_path:
            status = "success"
            self._notifier.extraction_success(
                output_path=output_path,
                city=city,
                ok_count=ok_count,
                total_count=total_count,
                duration_text=duration_text,
                scheduled=self._run_is_scheduled,
            )
        elif self._last_scrape_error:
            status = "failed"
            self._notifier.extraction_failed(
                self._last_scrape_error,
                scheduled=self._run_is_scheduled,
            )
        else:
            status = "no_results"
            self._notifier.extraction_no_results(scheduled=self._run_is_scheduled)

        if self._run_is_scheduled:
            settings = dict(settings)
            settings.setdefault("mode", "single")
            self._record_scheduler_run(
                status=status,
                settings=settings,
                output_path=output_path if status == "success" else "",
                ok_count=ok_count,
                total_posts=total_count,
                duration_seconds=duration_seconds,
                error_message=self._last_scrape_error if status == "failed" else "",
            )

    def _check_license_expiry_notice(self, info: Dict[str, Any]) -> None:
        expires = info.get("expires_at")
        if not expires:
            return
        try:
            from datetime import datetime, timezone

            exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            days = (exp - datetime.now(timezone.utc)).days
            if 0 < days <= 7:
                self._notifier.license_expiring_soon(days_left=days)
        except Exception:
            pass

    def _set_window_icon(self) -> None:
        try:
            ico_path = get_resource_path(ICON_ICO_ASSET)
            if os.path.isfile(ico_path):
                self.iconbitmap(ico_path)
                return
            logo_path = get_logo_path()
            if not os.path.isfile(logo_path):
                return
            from PIL import Image, ImageTk

            img = Image.open(logo_path)
            photo = ImageTk.PhotoImage(img)
            self.iconphoto(True, photo)
            self._window_icon = photo
        except Exception:
            pass

    def _apply_startup_window(self) -> None:
        """اندازه و موقعیت پنجره — اولین اجرا تمام‌صفحه، بعداً بازیابی تنظیم ذخیره‌شده."""
        self.update_idletasks()
        window_cfg = self._settings.get("window") or {}
        if not window_cfg.get("initialized"):
            self._maximize_window()
            return
        if window_cfg.get("maximized"):
            self._maximize_window()
            return
        geometry = str(window_cfg.get("geometry") or "").strip()
        if geometry and self._restore_window_geometry(geometry):
            return
        self._maximize_window()

    def _maximize_window(self) -> None:
        try:
            if sys.platform in ("win32", "darwin"):
                self.state("zoomed")
                return
        except Exception:
            pass
        try:
            w = self.winfo_screenwidth()
            h = max(MIN_WINDOW_H, self.winfo_screenheight() - 40)
            self.geometry(f"{w}x{h}+0+0")
        except Exception:
            self._center_window(1280, 860)

    def _center_window(self, width: int, height: int) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = min(width, sw)
        h = min(height, max(MIN_WINDOW_H, sh - 48))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _restore_window_geometry(self, geometry: str) -> bool:
        try:
            parts = geometry.split("+")
            if not parts or "x" not in parts[0]:
                return False
            w_str, h_str = parts[0].split("x", 1)
            w, h = int(w_str), int(h_str)
            if w < MIN_WINDOW_W or h < MIN_WINDOW_H:
                return False
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            if w > sw or h > sh:
                return False
            if len(parts) >= 3:
                x, y = int(parts[1]), int(parts[2])
                if x < -w + 80 or y < -h + 80 or x > sw - 40 or y > sh - 40:
                    self._center_window(w, h)
                    return True
                self.geometry(f"{w}x{h}+{x}+{y}")
                return True
            self._center_window(w, h)
            return True
        except Exception:
            return False

    def _capture_window_state(self) -> Dict[str, Any]:
        maximized = False
        try:
            maximized = str(self.state()) == "zoomed"
        except Exception:
            pass
        geometry = ""
        if not maximized:
            try:
                geometry = self.geometry()
            except Exception:
                geometry = ""
        return {
            "initialized": True,
            "maximized": maximized,
            "geometry": geometry,
        }

    def _save_window_state(self) -> None:
        self._settings["window"] = self._capture_window_state()
        self._storage.save_settings(self._settings)

    def _init_tray_and_shutdown(self) -> None:
        self._shutdown = ShutdownManager(
            schedule_ui=lambda ms, fn: self.after(ms, fn),
            is_busy=lambda: bool(self._execution.is_running or (self._worker and self._worker.is_alive())),
            request_cancel=self._cancel,
            stop_scheduler=self._shutdown_stop_scheduler,
            stop_tray=self._shutdown_stop_tray,
            save_state=self._shutdown_save_state,
            destroy_app=self._shutdown_destroy,
            join_worker=self._join_worker,
            on_progress=lambda msg: self.after(0, lambda m=msg: self._set_status_message(m, tone="brand")),
        )
        if not is_system_tray_supported():
            return
        self._tray = SystemTrayService(
            schedule_ui=lambda fn: self.after(0, fn),
            on_show=self._restore_from_tray,
            on_quit=self._quit_application,
            on_open_output=self._open_output_folder,
            on_stop_operation=self._tray_stop_operation,
            on_open_scheduler=self._tray_open_scheduler,
            on_show_status=self._tray_show_status,
            get_status_detail=self._tray_status_detail_text,
        )
        started = self._tray.start()
        if started:
            self._sync_tray_status()
            self._tray_status_poll_id = self.after(1500, self._poll_tray_status)

    def _shutdown_stop_scheduler(self) -> None:
        try:
            if getattr(self, "_scheduler", None) and self._scheduler.is_running:
                self._scheduler_running = False
                self._scheduler.stop()
                sch = self._settings.get("scheduler") or {}
                sch["enabled"] = False
                self._settings["scheduler"] = sch
        except Exception:
            pass

    def _shutdown_stop_tray(self) -> None:
        poll_id = getattr(self, "_tray_status_poll_id", None)
        if poll_id is not None:
            try:
                self.after_cancel(poll_id)
            except Exception:
                pass
            self._tray_status_poll_id = None
        tray = getattr(self, "_tray", None)
        if tray is not None:
            tray.stop()

    def _shutdown_save_state(self) -> None:
        try:
            if not self._hidden_to_tray:
                self._save_window_state()
            else:
                self._storage.save_settings(self._settings)
        except Exception:
            pass

    def _shutdown_destroy(self) -> None:
        try:
            self.destroy()
        except Exception:
            pass

    def _join_worker(self, timeout: float) -> bool:
        worker = self._worker
        if worker is None or not worker.is_alive():
            return True
        worker.join(timeout=timeout)
        return not worker.is_alive()

    def _quit_application(self) -> None:
        if self._shutdown and self._shutdown.is_shutting_down:
            return
        if self._hidden_to_tray:
            try:
                self._restore_from_tray()
            except Exception:
                pass
        if self._execution.is_running:
            if not messagebox.askyesno(
                "خروج کامل",
                "یک عملیات در حال اجراست.\nبا خروج، عملیات متوقف می‌شود. ادامه می‌دهید؟",
            ):
                return
        if self._shutdown:
            self._shutdown.request_shutdown(reason="quit")
        else:
            try:
                self._save_window_state()
            except Exception:
                pass
            self.destroy()

    def _on_close(self) -> None:
        if self._shutdown and self._shutdown.is_shutting_down:
            return
        prefs = parse_tray_prefs(self._settings)
        tray_ok = bool(self._tray and self._tray.available)
        if prefs.close_to_tray and tray_ok:
            if prefs.show_close_hint:
                self._show_close_to_tray_hint()
            else:
                self._hide_to_tray()
            return
        self._quit_application()

    def _show_close_to_tray_hint(self) -> None:
        existing = getattr(self, "_close_hint_dialog", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        def on_confirm(dont_show: bool) -> None:
            self._close_hint_dialog = None
            if dont_show:
                tray_cfg = dict(self._settings.get("tray") or default_tray_settings())
                tray_cfg["show_close_hint"] = False
                self._settings["tray"] = tray_cfg
                try:
                    self._storage.save_settings(self._settings)
                except Exception:
                    pass
                if hasattr(self, "_tray_close_to_tray_var"):
                    # فقط hint؛ close_to_tray دست‌نخورده
                    pass
            self._hide_to_tray()

        def on_quit() -> None:
            self._close_hint_dialog = None
            self._quit_application()

        self._close_hint_dialog = CloseToTrayDialog(
            self,
            on_confirm=on_confirm,
            on_quit_instead=on_quit,
        )

    def _hide_to_tray(self) -> None:
        if not self._tray or not self._tray.available:
            self._quit_application()
            return
        try:
            if not self._hidden_to_tray:
                self._save_window_state()
        except Exception:
            pass
        # Toast قبل از مخفی‌شدن تا کاربر ببیند
        try:
            Toast.show(self, "برنامه در System Tray فعال است", tone="info")
        except Exception:
            pass
        try:
            self.withdraw()
        except Exception:
            pass
        self._hidden_to_tray = True
        if not self._tray.is_running:
            self._tray.start()
        self._sync_tray_status()
        self._set_status_message("اجرا در پس‌زمینه (System Tray)", tone="brand")

    def _restore_from_tray(self) -> None:
        if self._shutdown and self._shutdown.is_shutting_down:
            return
        self._hidden_to_tray = False
        try:
            self.deiconify()
        except Exception:
            pass
        try:
            window_cfg = self._settings.get("window") or {}
            if window_cfg.get("maximized"):
                self.state("zoomed")
            else:
                self.state("normal")
        except Exception:
            try:
                self.state("normal")
            except Exception:
                pass
        try:
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(120, lambda: self.attributes("-topmost", False))
        except Exception:
            pass
        self._sync_tray_status()
        self._set_status_message("آماده", tone="success")

    def _tray_stop_operation(self) -> None:
        if self._execution.is_running:
            self._cancel()
            Toast.show(self, "درخواست توقف ارسال شد", tone="warning")
        else:
            Toast.show(self, "عملیات فعالی برای توقف نیست", tone="info")

    def _tray_open_scheduler(self) -> None:
        self._restore_from_tray()
        try:
            self._switch_tab("schedule")
        except Exception:
            pass

    def _tray_show_status(self) -> None:
        detail = self._tray_status_detail_text()
        if not self._hidden_to_tray:
            try:
                Toast.show(self, detail, tone="info")
            except Exception:
                pass
        try:
            self._notifier.status_info(
                title=f"وضعیت {SITE_DISPLAY_NAME}",
                message=detail,
            )
        except Exception:
            pass

    def _tray_status_detail_text(self) -> str:
        state = self._execution.state
        task = ""
        try:
            if hasattr(self, "current_task_lbl"):
                task = str(self.current_task_lbl.cget("text") or "").strip()
        except Exception:
            task = ""

        if state == ExecutionState.CANCELLING:
            return "در حال توقف عملیات…"
        if state == ExecutionState.RUNNING_BATCH:
            idx = self._batch_job_index + 1
            total = max(1, self._batch_job_total)
            base = f"Batch {fa_digits(idx)}/{fa_digits(total)}"
            return f"{base} — {task}" if task else base
        if state == ExecutionState.RUNNING_SINGLE:
            if "آپلود" in task:
                return task or "در حال آپلود…"
            if self._run_is_scheduled:
                return task or "استخراج زمان‌بندی‌شده…"
            return task or "در حال استخراج…"
        if getattr(self, "_scheduler", None) and self._scheduler.is_running:
            rem = self._scheduler.remaining_seconds
            if rem is not None:
                return f"زمان‌بندی فعال — اجرای بعدی حدود {format_duration_fa(rem)}"
            return "زمان‌بندی فعال"
        if self._hidden_to_tray:
            return "آماده · در پس‌زمینه"
        return "آماده"

    def _resolve_tray_status(self) -> tuple[TrayStatus, str]:
        state = self._execution.state
        detail = self._tray_status_detail_text()
        if state == ExecutionState.CANCELLING:
            return TrayStatus.CANCELLING, detail
        if state == ExecutionState.RUNNING_BATCH:
            return TrayStatus.BATCH, detail
        if state == ExecutionState.RUNNING_SINGLE:
            if "آپلود" in detail:
                return TrayStatus.UPLOADING, detail
            return TrayStatus.EXTRACTING, detail
        if self._last_scrape_error and not self._execution.is_idle:
            return TrayStatus.ERROR, self._last_scrape_error[:80]
        if getattr(self, "_scheduler", None) and self._scheduler.is_running:
            return TrayStatus.SCHEDULER, detail
        if self._hidden_to_tray:
            return TrayStatus.HIDDEN, detail
        return TrayStatus.READY, detail

    def _sync_tray_status(self) -> None:
        tray = getattr(self, "_tray", None)
        if not tray or not tray.available:
            return
        status, detail = self._resolve_tray_status()
        tray.set_status(status, detail)

    def _poll_tray_status(self) -> None:
        if self._shutdown and self._shutdown.is_shutting_down:
            return
        self._sync_tray_status()
        self._tray_status_poll_id = self.after(1500, self._poll_tray_status)

    # ── UI ──────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._build_statusbar()

    def _build_header(self) -> None:
        wrap = ctk.CTkFrame(self, fg_color=COLORS["header_bg"], corner_radius=0)
        wrap.grid(row=0, column=0, sticky="ew")
        wrap.grid_columnconfigure(0, weight=1)

        header = AppHeader(
            wrap,
            brand_name=SITE_DISPLAY_NAME,
            brand_tagline="استخراج حرفه‌ای آگهی‌های املاک",
            logo_image=self._brand_logo_image(28),
            on_notifications_click=self._open_header_notifications,
            on_settings_click=self._open_header_settings,
            on_profile_click=self._open_header_profile,
        )
        header.grid(row=0, column=0, sticky="ew")

        ctk.CTkFrame(wrap, height=1, fg_color=COLORS["header_border"]).grid(
            row=1, column=0, sticky="ew",
        )

        from app.ui.components.navigation import SegmentedNav

        self._nav = SegmentedNav(wrap, on_change=self._switch_tab)
        self._nav.grid(row=2, column=0, sticky="ew")
        self._nav.add_tabs(("extract", "output", "schedule", "license", "settings", "about"))

        self._header = header
        self._header.nav = self._nav  # سازگاری با کد قبلی
        self._tab_vars = self._nav._tabs

        self._active_tab = "extract"

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=SPACE_SM, pady=0)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        canvas = AppCanvas(body)
        canvas.grid(row=0, column=0, sticky="nsew")
        canvas.grid_columnconfigure(0, weight=1)
        canvas.grid_rowconfigure(0, weight=1)

        self._pages: Dict[str, ctk.CTkFrame] = {}
        self._pages_container = ctk.CTkFrame(canvas, fg_color="transparent")
        self._pages_container.grid(row=0, column=0, sticky="nsew", padx=SPACE_SM, pady=SPACE_SM)
        self._pages_container.grid_columnconfigure(0, weight=1)
        self._pages_container.grid_rowconfigure(0, weight=1)

        self._pages["extract"] = build_extraction_page(self)
        self._pages["output"] = build_output_page(self)
        self._pages["schedule"] = build_schedule_page(self)
        self._pages["license"] = build_license_page(self)
        self._wire_account_login_panel()
        self._pages["settings"] = build_settings_page(self)
        self._pages["about"] = build_about_page(self)

        self._switch_tab("extract")

    def _entry(self, parent, *, readonly: bool = False, **kwargs) -> ctk.CTkEntry:
        entry = styled_entry(parent, **kwargs)
        enable_entry_shortcuts(entry, readonly=readonly)
        return entry

    def _build_statusbar(self) -> None:
        self._statusbar = AppStatusBar(self)
        self._statusbar.grid(row=2, column=0, sticky="ew")
        self.status_lbl = self._statusbar.status_lbl
        self._stat_extract = self._statusbar._stat_extract
        self._stat_license = self._statusbar._stat_license
        self.status_path_lbl = self._statusbar.status_path_lbl

    def _set_status_message(self, text: str, *, tone: str = "muted") -> None:
        self._statusbar.set_message(text, tone=tone)

    def _reset_stat_cards(self) -> None:
        for attr in ("_stat_card_total", "_stat_card_done", "_stat_card_ok"):
            card = getattr(self, attr, None)
            if card is not None:
                card.set_value("—")
        if hasattr(self, "stat_total"):
            self.stat_total.configure(text="کل: —")
        if hasattr(self, "stat_done"):
            self.stat_done.configure(text="انجام‌شده: —")
        if hasattr(self, "stat_success"):
            self.stat_success.configure(text="موفق: —")

    def _update_stat_cards(
        self,
        *,
        total: int = 0,
        done: int = 0,
        ok: int = 0,
    ) -> None:
        # طرح: استخراج‌شده | موفق | زمان گذشته
        extracted = done or total
        if hasattr(self, "_stat_card_total"):
            self._stat_card_total.set_value(f"{fa_digits(extracted)} آگهی")
        if hasattr(self, "_stat_card_done"):
            suffix = " دسته" if getattr(self, "_active_batch_run", False) else ""
            self._stat_card_done.set_value(f"{fa_digits(ok)}{suffix}")
        if hasattr(self, "stat_done"):
            self.stat_done.configure(text=f"{fa_digits(done)} از {fa_digits(total)} آگهی" if total else f"{fa_digits(done)} آگهی")
        if hasattr(self, "stat_total"):
            self.stat_total.configure(text="")
        if hasattr(self, "stat_success"):
            self.stat_success.configure(text="")
        # زمان گذشته از scrape_time_info همگام می‌شود
        if hasattr(self, "scrape_time_info") and hasattr(self, "_stat_card_ok"):
            t = self.scrape_time_info.cget("text") or "—"
            if t.startswith("مدت کل:"):
                t = t.replace("مدت کل:", "").strip()
            elif t.startswith("زمان باقی‌مانده تقریبی:"):
                pass
            if self.scrape_start_time:
                elapsed = time.time() - self.scrape_start_time
                mins, secs = divmod(int(elapsed), 60)
                self._stat_card_ok.set_value(f"{fa_digits(mins)}:{fa_digits(f'{secs:02d}')} دقیقه")


    @staticmethod
    def _truncate_status_path(path: str, max_len: int = 72) -> str:
        path = (path or "").strip()
        if not path:
            return ""
        if len(path) <= max_len:
            return path
        return "…" + path[-(max_len - 1):]

    def _sync_status_path(self, path: str = "") -> None:
        if not hasattr(self, "status_path_lbl"):
            return
        if path:
            self.status_path_lbl.configure(text=self._truncate_status_path(path))
            return
        try:
            preview = ExtractionEngine.preview_output_structure(
                self._collect_settings(), self._places,
            )
            self.status_path_lbl.configure(
                text=f"خروجی: {preview}" if preview else "",
            )
        except Exception:
            self.status_path_lbl.configure(text="")

    def _switch_tab(self, key: str) -> None:
        self._active_tab = key
        for name, page in self._pages.items():
            if name == key:
                page.grid(row=0, column=0, sticky="nsew")
            else:
                page.grid_forget()
        if hasattr(self, "_header"):
            if hasattr(self, "_nav"):
                self._nav.set_active(key)
            elif hasattr(self._header, "nav"):
                self._header.nav.set_active(key)

    def _flash_panel(self, panel, *, normal_border=None, highlight_border=None) -> None:
        if panel is None:
            return
        try:
            normal = normal_border or COLORS["card_border"]
            highlight = highlight_border or COLORS["primary"]
            panel.configure(border_width=1, border_color=highlight)

            def _restore() -> None:
                try:
                    panel.configure(border_width=1, border_color=normal)
                except Exception:
                    pass

            self.after(1200, _restore)
        except Exception:
            pass

    def _open_header_settings(self) -> None:
        self._switch_tab("settings")
        self._set_status_message("صفحه تنظیمات باز شد", tone="info")
        Toast.show(self, "تنظیمات باز شد", tone="info")
        self._flash_panel(getattr(self, "_settings_conn_panel", None))

    def _open_header_notifications(self) -> None:
        self._switch_tab("settings")
        self._set_status_message("بخش اعلان‌ها باز شد", tone="info")
        Toast.show(self, "اعلان‌ها و تست نوتیفیکیشن", tone="info")
        self._flash_panel(getattr(self, "_notify_panel", None))

    def _open_header_profile(self) -> None:
        self._switch_tab("license")
        self._set_status_message("بخش لایسنس و پروفایل باز شد", tone="info")
        Toast.show(self, "لایسنس و پروفایل", tone="info")
        target = getattr(self, "_license_profile_panel", None)
        if target is None or not target.winfo_ismapped():
            target = getattr(self, "_license_activate_panel", None)
        self._flash_panel(target)

    def _update_output_file_display(self, path: str) -> None:
        import os
        from datetime import datetime

        if hasattr(self, "_output_file_field"):
            self._output_file_field.set_value(path, muted=False)
        if hasattr(self, "last_file_lbl"):
            display = path
            if len(display) > 64:
                display = "…" + display[-61:]
            self.last_file_lbl.configure(text=display, text_color=COLORS["text_primary"])
        if hasattr(self, "_out_stat_file"):
            self._out_stat_file.set_value(os.path.basename(path) or "—")
        if hasattr(self, "_out_stat_time"):
            self._out_stat_time.set_value(
                fa_digits(datetime.now().strftime("%H:%M")) + " امروز",
            )
        if hasattr(self, "_out_stat_size") and os.path.isfile(path):
            size = os.path.getsize(path)
            if size > 1_048_576:
                self._out_stat_size.set_value(f"{size // 1_048_576} MB")
            elif size > 1024:
                self._out_stat_size.set_value(f"{size // 1024} KB")
            else:
                self._out_stat_size.set_value(f"{size} B")
        if hasattr(self, "_output_empty"):
            self._output_empty.pack_forget()

    def _copy_output_dir(self) -> None:
        path = get_output_dir()
        try:
            self.clipboard_clear()
            self.clipboard_append(path)
            self._set_status_message("مسیر پوشه خروجی کپی شد", tone="success")
            Toast.show(self, "مسیر کپی شد", tone="success")
        except Exception:
            messagebox.showwarning("کپی", "امکان کپی مسیر وجود ندارد.")

    # ── Startup ─────────────────────────────────────────────────────────
    def _startup(self) -> None:
        try:
            self._places.load()
            self.province_cb.configure(values=self._places.province_names(), state="readonly")
            self.province_cb.set("")
            self.sch_province_cb.configure(values=self._places.province_names(), state="readonly")
            self.sch_province_cb.set("")
            self.sch_transaction_cb.set("فروش مسکونی")
            self._set_sch_subcategories("فروش مسکونی")
            for cb in (
                self.transaction_type_cb, self.subcategory_cb,
                self.province_cb, self.city_cb, self.district_cb,
                self.sch_province_cb, self.sch_city_cb, self.sch_district_cb,
                self.sch_transaction_cb, self.sch_subcategory_cb, self.sch_interval_cb,
            ):
                apply_combobox_rtl(cb)
        except Exception as exc:
            messagebox.showerror("خطا", f"بارگذاری مکان‌ها: {exc}")
        self._check_license_on_startup()
        self._restore_extraction_settings()
        self._restore_scheduler_settings()
        self._sync_status_path()
        self._switch_tab("extract" if self.license_validated else "license")

    def _restore_extraction_settings(self) -> None:
        ext = self._settings.get("extraction") or {}
        if not ext:
            return
        try:
            if ext.get("transaction_type"):
                self.transaction_type_cb.set(ext["transaction_type"])
                self._on_transaction_changed(ext["transaction_type"])
            if ext.get("subcategory"):
                self.subcategory_cb.set(ext["subcategory"])
            if ext.get("max_items"):
                self.items_slider.set(float(ext["max_items"]))
                self._on_items_changed(ext["max_items"])
            if ext.get("output_format"):
                self.output_format.set(ext["output_format"])
            if ext.get("download_images"):
                self.download_images_cb.select()
            if "upload_to_platform" in ext:
                self._upload_platform_var.set(bool(ext["upload_to_platform"]))
            else:
                self._upload_platform_var.set(True)
            flt = ext.get("filters") or {}
            from app.filter_utils import normalize_filter_value

            self._advertiser_filter.set(normalize_filter_value(flt.get("advertiser_filter", "all")))
            if hasattr(self, "search_query_entry") and flt.get("search_query"):
                self.search_query_entry.delete(0, "end")
                self.search_query_entry.insert(0, str(flt["search_query"]))
            self._restore_advanced_filters(flt)
            if ext.get("province"):
                self.province_cb.set(ext["province"])
                self._on_province_changed(ext["province"])
            if ext.get("city"):
                self.city_cb.set(ext["city"])
                self._on_city_changed(ext["city"])
            if ext.get("district"):
                self.district_cb.set(ext["district"])
            self._update_path_preview()
            self._update_advanced_filter_visibility()
        except Exception:
            pass

    def _current_subcategory_api(self) -> str:
        tx = self.transaction_type_cb.get() if hasattr(self, "transaction_type_cb") else ""
        sub = self.subcategory_cb.get() if hasattr(self, "subcategory_cb") else ""
        for item in TRANSACTION_TYPES.get(tx, {}).get("subcategories", []):
            if item.get("label") == sub:
                return str(item.get("api") or "")
        return ""

    def _collect_advanced_filters(self) -> Dict[str, Any]:
        if not hasattr(self, "_price_filter_row"):
            return normalize_saved_filters({})
        p_min, p_max = self._price_filter_row.get_values()
        d_min, d_max = self._deposit_filter_row.get_values()
        r_min, r_max = self._rent_filter_row.get_values()
        a_min, a_max = self._area_filter_row.get_values()
        y_min, y_max = self._year_filter_row.get_values()
        amenity_vars = getattr(self, "_amenity_filter_vars", {})
        return {
            "price_min": p_min,
            "price_max": p_max,
            "deposit_min": d_min,
            "deposit_max": d_max,
            "rent_min": r_min,
            "rent_max": r_max,
            "area_min": a_min,
            "area_max": a_max,
            "year_min": y_min,
            "year_max": y_max,
            "parking": bool(amenity_vars.get("parking") and amenity_vars["parking"].get()),
            "warehouse": bool(amenity_vars.get("warehouse") and amenity_vars["warehouse"].get()),
            "elevator": bool(amenity_vars.get("elevator") and amenity_vars["elevator"].get()),
            "advertiser_filter": self._advertiser_filter.get() or "all",
            "search_query": (
                self.search_query_entry.get().strip()
                if hasattr(self, "search_query_entry")
                else ""
            ),
        }

    def _restore_advanced_filters(self, flt: Optional[Dict[str, Any]] = None) -> None:
        if not hasattr(self, "_price_filter_row"):
            return
        saved = normalize_saved_filters(flt)
        if any(
            saved.get(k) not in (None, "")
            for k in (
                "price_min", "price_max", "deposit_min", "deposit_max",
                "rent_min", "rent_max", "area_min", "area_max",
                "year_min", "year_max",
            )
        ) or any(saved.get(k) for k in ("parking", "warehouse", "elevator")):
            if hasattr(self, "_adv_filters_expanded"):
                self._adv_filters_expanded.set(True)
                if hasattr(self, "_toggle_adv_filters"):
                    self._toggle_adv_filters()
        self._price_filter_row.set_values(
            format_filter_int(saved.get("price_min")),
            format_filter_int(saved.get("price_max")),
        )
        self._deposit_filter_row.set_values(
            format_filter_int(saved.get("deposit_min")),
            format_filter_int(saved.get("deposit_max")),
        )
        self._rent_filter_row.set_values(
            format_filter_int(saved.get("rent_min")),
            format_filter_int(saved.get("rent_max")),
        )
        self._area_filter_row.set_values(
            format_filter_int(saved.get("area_min")),
            format_filter_int(saved.get("area_max")),
        )
        self._year_filter_row.set_values(
            format_filter_int(saved.get("year_min")),
            format_filter_int(saved.get("year_max")),
        )
        for key, var in getattr(self, "_amenity_filter_vars", {}).items():
            var.set(bool(saved.get(key)))

    def _update_advanced_filter_visibility(self) -> None:
        if not hasattr(self, "_money_host"):
            return
        for row in (
            getattr(self, "_price_filter_row", None),
            getattr(self, "_deposit_filter_row", None),
            getattr(self, "_rent_filter_row", None),
        ):
            if row is not None:
                row.pack_forget()
        expanded = bool(
            getattr(self, "_adv_filters_expanded", ctk.BooleanVar(value=False)).get()
        )
        if not expanded:
            return
        tx = self.transaction_type_cb.get() if hasattr(self, "transaction_type_cb") else ""
        if is_rent_transaction(tx):
            self._deposit_filter_row.pack(fill="x", pady=(0, SPACE_XS))
            self._rent_filter_row.pack(fill="x", pady=(0, SPACE_SM))
        else:
            self._price_filter_row.pack(fill="x", pady=(0, SPACE_SM))

        amenity_vars = getattr(self, "_amenity_filter_vars", {})
        amenity_checks = getattr(self, "_amenity_filter_checks", {})
        amenity_row = getattr(self, "_amenity_filter_row", None)
        base_api = self._current_subcategory_api()
        preview_filters = {
            key: bool(amenity_vars.get(key) and amenity_vars[key].get())
            for key in amenity_vars
        }
        effective_api = resolve_search_category(base_api, preview_filters)
        supported = supported_amenities_for_category(effective_api)
        if amenity_row is not None:
            if supported:
                amenity_row.pack(fill="x", pady=(0, SPACE_XS))
            else:
                amenity_row.pack_forget()
        for key, var in amenity_vars.items():
            cb = amenity_checks.get(key)
            if key not in supported:
                var.set(False)
                if cb is not None:
                    cb.configure(state="disabled")
            elif cb is not None:
                cb.configure(state="normal")

    # ── Places handlers ─────────────────────────────────────────────────
    def _set_subcategories_for_transaction(self, selected: str, update_preview: bool = True) -> None:
        subs = TRANSACTION_TYPES.get(selected, {}).get("subcategories", [])
        labels = [s["label"] for s in subs]
        self.subcategory_cb.configure(values=labels, state="readonly" if labels else "disabled")
        if labels:
            self.subcategory_cb.set(labels[0])
        if update_preview:
            self._update_path_preview()

    def _on_transaction_changed(self, selected: str) -> None:
        self._set_subcategories_for_transaction(selected, update_preview=True)
        self._update_advanced_filter_visibility()
        update_summary_chips(self)

    def _on_subcategory_changed(self, _selected: str) -> None:
        self._update_path_preview()
        self._update_advanced_filter_visibility()

    def _on_province_changed(self, name: str) -> None:
        cities = self._places.city_names_for_province(name)
        self.city_cb.configure(values=cities, state="readonly" if cities else "disabled")
        self.city_cb.set("")
        self.district_cb.configure(values=["—"], state="disabled")
        self.district_cb.set("—")
        self._update_path_preview()
        update_summary_chips(self)

    def _on_city_changed(self, name: str) -> None:
        districts = self._places.district_names_for_city(name)
        self.district_cb.configure(values=districts, state="readonly" if len(districts) > 1 else "disabled")
        self.district_cb.set("—")
        self._update_path_preview()
        update_summary_chips(self)

    def _on_district_changed(self, _name: str) -> None:
        self._update_path_preview()
        update_summary_chips(self)

    def _set_sch_subcategories(self, selected: str) -> None:
        subs = TRANSACTION_TYPES.get(selected, {}).get("subcategories", [])
        labels = [s["label"] for s in subs]
        self.sch_subcategory_cb.configure(values=labels, state="readonly" if labels else "disabled")
        if labels:
            self.sch_subcategory_cb.set(labels[0])

    def _on_sch_transaction_changed(self, selected: str) -> None:
        self._set_sch_subcategories(selected)
        self._update_schedule_summary()

    def _on_sch_province_changed(self, name: str) -> None:
        cities = self._places.city_names_for_province(name)
        self.sch_city_cb.configure(values=cities, state="readonly" if cities else "disabled")
        self.sch_city_cb.set("")
        self.sch_district_cb.configure(values=["—"], state="disabled")
        self.sch_district_cb.set("—")
        self._update_schedule_summary()

    def _on_sch_city_changed(self, name: str) -> None:
        districts = self._places.district_names_for_city(name)
        self.sch_district_cb.configure(
            values=districts, state="readonly" if len(districts) > 1 else "disabled",
        )
        self.sch_district_cb.set("—")
        self._update_schedule_summary()

    def _on_place_search(self) -> None:
        query = self.place_search_entry.get().strip()
        result = self._places.search_and_resolve(query)
        if not result:
            self._emit("مکان مورد نظر یافت نشد", "warning")
            return
        prov_id, city_id, dist_id = result
        p_name, c_name, d_name = self._places.get_names_for_ids(prov_id, city_id, dist_id)
        if p_name:
            self.province_cb.set(p_name)
            self._on_province_changed(p_name)
        if c_name:
            self.city_cb.set(c_name)
            self._on_city_changed(c_name)
        if d_name:
            self.district_cb.set(d_name)
        self._emit(f"مکان «{query}» انتخاب شد.", "success")

    def _on_items_changed(self, value: float) -> None:
        val = int(round(float(value)))
        if hasattr(self, "items_value_lbl"):
            self.items_value_lbl.configure(text=f"{fa_digits(val)} آگهی")
        if hasattr(self, "_batch_panel"):
            self._batch_panel._update_summary()
        self._refresh_start_button_label()
        update_summary_chips(self)

    def _on_sch_items_changed(self, value: float) -> None:
        val = int(round(float(value)))
        if hasattr(self, "sch_items_value_lbl"):
            text = "بدون استخراج" if val == 0 else f"{fa_digits(val)} آگهی"
            self.sch_items_value_lbl.configure(text=text)
        self._update_schedule_summary()

    def _set_sch_items(self, value: int) -> None:
        val = max(0, min(SCHEDULER_MAX_ITEMS, int(value)))
        if hasattr(self, "sch_items_slider"):
            self.sch_items_slider.set(float(val))
        self._on_sch_items_changed(val)

    def _set_sch_interval_hours(self, hours: float) -> None:
        mode = getattr(self, "_sch_mode", "single")
        hours = clamp_interval_for_mode(float(hours), mode=mode)
        if hasattr(self, "sch_interval_cb"):
            self.sch_interval_cb.set(hours_to_interval_label(hours, mode=mode))
        self._update_schedule_summary()
        self._refresh_scheduler_live_banner()

    def _on_sch_mode_changed(self, mode: str) -> None:
        if mode not in ("single", "batch"):
            return
        self._sch_mode = mode
        if hasattr(self, "_sch_mode_selector"):
            self._sch_mode_selector.set_mode(mode, notify=False)

        if hasattr(self, "_sch_single_fields"):
            if mode == "single":
                self._sch_single_fields.pack(fill="x", pady=(0, SPACE_XS))
            else:
                self._sch_single_fields.pack_forget()
        if hasattr(self, "_sch_batch_host"):
            if mode == "batch":
                self._sch_batch_host.pack(fill="x", pady=(0, SPACE_XS))
            else:
                self._sch_batch_host.pack_forget()

        if hasattr(self, "sch_interval_cb"):
            labels = scheduler_interval_labels(mode=mode)
            current_hours = interval_label_to_hours(self.sch_interval_cb.get())
            clamped = clamp_interval_for_mode(current_hours, mode=mode)
            self.sch_interval_cb.configure(values=labels)
            self.sch_interval_cb.set(hours_to_interval_label(clamped, mode=mode))

        for hours, btn in getattr(self, "_sch_interval_chip_btns", {}).items():
            try:
                if mode == "batch" and float(hours) < SCHEDULER_BATCH_MIN_HOURS:
                    btn.configure(state="disabled", text_color=COLORS["text_muted"])
                else:
                    btn.configure(state="normal", text_color=COLORS["text_secondary"])
            except Exception:
                pass

        if hasattr(self, "_sch_interval_hint"):
            if mode == "batch":
                self._sch_interval_hint.configure(
                    text=f"حالت گروهی: حداقل بازه {fa_digits(int(SCHEDULER_BATCH_MIN_HOURS))} ساعت — برای پایداری سیستم.",
                )
            else:
                self._sch_interval_hint.configure(text="بازه دلخواه را انتخاب کنید؛ از ۳۰ دقیقه تا هفتگی.")

        self._update_schedule_summary()
        self._refresh_scheduler_live_banner()

    def _refresh_scheduler_live_banner(self) -> None:
        if not hasattr(self, "_sch_live_banner"):
            return
        try:
            sch = self._collect_scheduler_settings()
        except Exception:
            sch = dict(self._settings.get("scheduler") or {})
        mode = sch.get("mode") if sch.get("mode") in ("single", "batch") else "single"
        parts = [p for p in (sch.get("province"), sch.get("city"), sch.get("district")) if p and p != "—"]
        location = " / ".join(parts) if parts else ""
        job_count = 0
        if mode == "batch":
            if hasattr(self, "_sch_batch_panel"):
                job_count = self._sch_batch_panel.count_selected()
            else:
                job_count = len(sch.get("batch_job_keys") or [])
            preset = {
                "all": "همه دسته‌ها",
                "residential": "مسکونی",
                "commercial": "تجاری",
                "custom": "سفارشی",
            }.get(str(sch.get("batch_preset") or "all"), "گروهی")
            target = f"{preset} · {fa_digits(job_count)} زیردسته"
        else:
            cat = sch.get("transaction_type") or ""
            sub = sch.get("subcategory") or ""
            target = f"{cat} / {sub}".strip(" /") if cat or sub else ""

        running = bool(getattr(self, "_scheduler", None) and self._scheduler.is_running)
        extracting = bool(self._execution.is_running and self._run_is_scheduled)
        interval = hours_to_interval_label(float(sch.get("interval_hours") or 6), mode=mode)
        next_at = self._scheduler.next_run_at if running else None
        rem = self._scheduler.remaining_seconds if running else None
        self._sch_live_banner.update_state(
            running=running,
            extracting=extracting,
            location=location,
            target=target,
            interval_label=interval,
            next_run_at=next_at,
            remaining_seconds=rem,
            mode=mode,
            job_count=job_count if mode == "batch" else 0,
        )
        if hasattr(self, "_sch_footer_target"):
            if location or target:
                self._sch_footer_target.configure(text=f"{location or '—'} · {target or '—'}")
            else:
                self._sch_footer_target.configure(text="")

    def _copy_extraction_to_scheduler(self) -> None:
        """کپی محدوده و دسته از تب استخراج به زمان‌بندی."""
        try:
            if hasattr(self, "province_cb") and self.province_cb.get():
                self.sch_province_cb.set(self.province_cb.get())
                self._on_sch_province_changed(self.province_cb.get())
            if hasattr(self, "city_cb") and self.city_cb.get():
                self.sch_city_cb.set(self.city_cb.get())
                self._on_sch_city_changed(self.city_cb.get())
            if hasattr(self, "district_cb") and self.district_cb.get():
                self.sch_district_cb.set(self.district_cb.get())
            if hasattr(self, "transaction_type_cb") and self.transaction_type_cb.get():
                self.sch_transaction_cb.set(self.transaction_type_cb.get())
                self._set_sch_subcategories(self.transaction_type_cb.get())
            if hasattr(self, "subcategory_cb") and self.subcategory_cb.get():
                self.sch_subcategory_cb.set(self.subcategory_cb.get())
            if hasattr(self, "items_slider") and hasattr(self, "sch_items_slider"):
                raw = int(round(float(self.items_slider.get())))
                raw = max(0, min(SCHEDULER_MAX_ITEMS, raw))
                self.sch_items_slider.set(float(raw))
                self._on_sch_items_changed(raw)
            if hasattr(self, "output_format") and hasattr(self, "_sch_output_format"):
                self._sch_output_format.set(self.output_format.get())
                for val, btn in getattr(self, "_sch_format_btns", {}).items():
                    active = val == self.output_format.get()
                    btn.configure(
                        fg_color=COLORS["primary"] if active else "transparent",
                        text_color=COLORS["accent_text"] if active else COLORS["text_secondary"],
                    )
            if hasattr(self, "_upload_platform_var") and hasattr(self, "_sch_upload_var"):
                self._sch_upload_var.set(bool(self._upload_platform_var.get()))
            if hasattr(self, "download_images_cb") and hasattr(self, "sch_download_images_cb"):
                if self.download_images_cb.get():
                    self.sch_download_images_cb.select()
                else:
                    self.sch_download_images_cb.deselect()
            if hasattr(self, "search_query_entry") and hasattr(self, "sch_search_entry"):
                self.sch_search_entry.delete(0, "end")
                self.sch_search_entry.insert(0, self.search_query_entry.get())
            self._update_schedule_summary()
            self._set_status_message("تنظیمات استخراج به زمان‌بندی کپی شد", tone="success")
            Toast.show(self, "کپی از استخراج انجام شد", tone="success")
        except Exception as exc:
            self._set_status_message(f"کپی ناموفق: {exc}", tone="error")

    def _update_schedule_summary(self) -> None:
        if not hasattr(self, "_sch_summary_lbl"):
            return
        try:
            sch = self._collect_scheduler_settings()
        except Exception:
            return
        parts = [p for p in (sch.get("province"), sch.get("city"), sch.get("district")) if p and p != "—"]
        area = "، ".join(parts) if parts else "محدوده نامشخص"
        mode = sch.get("mode") if sch.get("mode") in ("single", "batch") else "single"
        if mode == "batch":
            count = self._sch_batch_panel.count_selected() if hasattr(self, "_sch_batch_panel") else 0
            preset = {
                "all": "همه زیردسته‌ها",
                "residential": "مسکونی",
                "commercial": "تجاری",
                "custom": "سفارشی",
            }.get(str(sch.get("batch_preset") or "all"), "گروهی")
            cat_txt = f"گروهی · {preset} · {fa_digits(count)} زیردسته"
        else:
            cat = sch.get("transaction_type") or "—"
            sub = sch.get("subcategory") or ""
            cat_txt = f"تکی · {cat}" + (f" / {sub}" if sub else "")
        items = int(sch.get("max_items") or 0)
        items_txt = "بدون استخراج" if items == 0 else f"{fa_digits(items)} آگهی"
        interval = hours_to_interval_label(float(sch.get("interval_hours") or 6), mode=mode)
        fmt = (sch.get("output_format") or "excel").upper()
        upload = "آپلود فعال" if sch.get("upload_to_platform") else "بدون آپلود"
        from app.filter_utils import ADVERTISER_FILTER_LABELS, normalize_filter_value

        adv = ADVERTISER_FILTER_LABELS.get(
            normalize_filter_value(sch.get("advertiser_filter")),
            "همه آگهی‌ها",
        )
        q = str(sch.get("search_query") or "").strip()
        q_txt = f" · جستجو: {q}" if q and mode == "single" else ""
        running = bool(getattr(self, "_scheduler", None) and self._scheduler.is_running)
        state_txt = "● روشن" if running else "○ خاموش"
        self._sch_summary_lbl.configure(
            text=(
                f"{state_txt}  ·  {area}  ·  {cat_txt}\n"
                f"{interval}  ·  {items_txt}  ·  {fmt}  ·  {upload}  ·  {adv}{q_txt}"
            ),
        )
        self._refresh_scheduler_live_banner()

    def _on_workers_changed(self, value: float) -> None:
        val = int(round(float(value)))
        self.workers_lbl.configure(text=fa_digits(val))
        scraper.CONFIG["max_workers"] = val

    def _on_appearance_changed(self, mode: str) -> None:
        if mode in ("light", "dark", "system"):
            ctk.set_appearance_mode(mode)

    def _reset_settings_defaults(self) -> None:
        workers_default = 6
        appearance_default = "light"

        self.workers_slider.set(float(workers_default))
        self._appearance_var.set(appearance_default)
        self._on_workers_changed(workers_default)
        self._on_appearance_changed(appearance_default)
        if hasattr(self, "_tray_close_to_tray_var"):
            self._tray_close_to_tray_var.set(True)
        if hasattr(self, "_notify_extraction_var"):
            self._notify_extraction_var.set(True)
        if hasattr(self, "_notify_errors_var"):
            self._notify_errors_var.set(True)
        self._set_status_message("مقادیر پیش‌فرض بارگذاری شد — برای اعمال دائمی ذخیره کنید", tone="brand")

    def _collect_settings(self) -> Dict[str, Any]:
        max_workers = int(self._settings.get("max_workers", 6))
        if hasattr(self, "workers_slider"):
            max_workers = int(round(float(self.workers_slider.get())))
        max_items = MAX_EXTRACTION_ITEMS
        if hasattr(self, "items_slider"):
            max_items = int(round(float(self.items_slider.get())))
        max_items = max(1, min(MAX_EXTRACTION_ITEMS, max_items))
        return {
            "transaction_type": self.transaction_type_cb.get() if hasattr(self, "transaction_type_cb") else "",
            "subcategory": self.subcategory_cb.get() if hasattr(self, "subcategory_cb") else "",
            "province": self.province_cb.get() if hasattr(self, "province_cb") else "",
            "city": self.city_cb.get() if hasattr(self, "city_cb") else "",
            "district": self.district_cb.get() if hasattr(self, "district_cb") else "",
            "max_items": max_items,
            "max_workers": max_workers,
            "output_format": self.output_format.get(),
            "download_images": bool(self.download_images_cb.get()) if hasattr(self, "download_images_cb") else False,
            "upload_to_platform": bool(self._upload_platform_var.get()),
            "filters": self._collect_advanced_filters(),
        }

    def _collect_scheduler_settings(self) -> Dict[str, Any]:
        max_items = 100
        if hasattr(self, "sch_items_slider"):
            max_items = int(round(float(self.sch_items_slider.get())))
        max_items = max(0, min(SCHEDULER_MAX_ITEMS, max_items))
        output_format = "excel"
        if hasattr(self, "_sch_output_format"):
            output_format = self._sch_output_format.get() or "excel"
        elif hasattr(self, "output_format"):
            output_format = self.output_format.get()
        upload = True
        if hasattr(self, "_sch_upload_var"):
            upload = bool(self._sch_upload_var.get())
        search_query = ""
        if hasattr(self, "sch_search_entry"):
            search_query = self.sch_search_entry.get().strip()
        run_now = True
        if hasattr(self, "_sch_run_now_var"):
            run_now = bool(self._sch_run_now_var.get())
        mode = getattr(self, "_sch_mode", "single")
        if mode not in ("single", "batch"):
            mode = "single"
        interval_hours = interval_label_to_hours(
            self.sch_interval_cb.get() if hasattr(self, "sch_interval_cb") else "هر ۶ ساعت",
        )
        interval_hours = clamp_interval_for_mode(interval_hours, mode=mode)
        batch_preset = "all"
        batch_job_keys: list = []
        if hasattr(self, "_sch_batch_panel"):
            state = self._sch_batch_panel.export_state()
            batch_preset = str(state.get("batch_preset") or "all")
            batch_job_keys = list(state.get("batch_job_keys") or [])
        return {
            "enabled": bool(getattr(self._scheduler, "is_running", False)),
            "mode": mode,
            "interval_hours": interval_hours,
            "transaction_type": self.sch_transaction_cb.get() if hasattr(self, "sch_transaction_cb") else "",
            "subcategory": self.sch_subcategory_cb.get() if hasattr(self, "sch_subcategory_cb") else "",
            "province": self.sch_province_cb.get() if hasattr(self, "sch_province_cb") else "",
            "city": self.sch_city_cb.get() if hasattr(self, "sch_city_cb") else "",
            "district": self.sch_district_cb.get() if hasattr(self, "sch_district_cb") else "",
            "max_items": max_items,
            "output_format": output_format,
            "download_images": bool(self.sch_download_images_cb.get()) if hasattr(self, "sch_download_images_cb") else False,
            "upload_to_platform": upload,
            "advertiser_filter": self._sch_advertiser_filter.get() or "all",
            "search_query": search_query,
            "run_immediately": run_now,
            "batch_preset": batch_preset,
            "batch_job_keys": batch_job_keys,
        }

    def _get_scheduler_run_config(self) -> Dict[str, Any]:
        """تنظیمات زمان‌بندی برای اجرا — مقادیر فعلی UI (مثل فیلتر شخصی) اولویت دارند."""
        saved = dict(self._settings.get("scheduler") or default_scheduler_config())
        live = self._collect_scheduler_settings()
        saved.update(live)
        saved["enabled"] = bool(self._scheduler.is_running)
        return saved

    def _scheduler_settings_to_run(self, sch: Dict[str, Any]) -> Dict[str, Any]:
        mode = sch.get("mode") if sch.get("mode") in ("single", "batch") else "single"
        return {
            "mode": mode,
            "transaction_type": sch.get("transaction_type") or "فروش مسکونی",
            "subcategory": sch.get("subcategory") or "",
            "province": sch.get("province") or "",
            "city": sch.get("city") or "",
            "district": sch.get("district") or "",
            "max_items": int(sch.get("max_items") or 100),
            "max_workers": int(self._settings.get("max_workers", 6)),
            "output_format": sch.get("output_format") or "excel",
            "download_images": bool(sch.get("download_images")),
            "upload_to_platform": bool(
                sch.get(
                    "upload_to_platform",
                    (self._settings.get("extraction") or {}).get("upload_to_platform", True),
                )
            ),
            "filters": {
                "advertiser_filter": sch.get("advertiser_filter", "all"),
                "search_query": str(sch.get("search_query") or "").strip(),
            },
            "batch_preset": sch.get("batch_preset") or "all",
            "batch_job_keys": list(sch.get("batch_job_keys") or []),
        }

    def _restore_scheduler_settings(self) -> None:
        sch = self._settings.get("scheduler") or default_scheduler_config()
        try:
            if sch.get("transaction_type"):
                self.sch_transaction_cb.set(sch["transaction_type"])
                self._set_sch_subcategories(sch["transaction_type"])
            if sch.get("subcategory"):
                self.sch_subcategory_cb.set(sch["subcategory"])
            if sch.get("province"):
                self.sch_province_cb.set(sch["province"])
                self._on_sch_province_changed(sch["province"])
            if sch.get("city"):
                self.sch_city_cb.set(sch["city"])
                self._on_sch_city_changed(sch["city"])
            if sch.get("district"):
                self.sch_district_cb.set(sch["district"])
            if hasattr(self, "_sch_mode_selector"):
                mode = sch.get("mode") if sch.get("mode") in ("single", "batch") else "single"
                self._on_sch_mode_changed(mode)
            if hasattr(self, "_sch_batch_panel"):
                self._sch_batch_panel.apply_state(
                    str(sch.get("batch_preset") or "all"),
                    sch.get("batch_job_keys") or [],
                )
            if hasattr(self, "sch_interval_cb"):
                mode = sch.get("mode") if sch.get("mode") in ("single", "batch") else "single"
                self.sch_interval_cb.set(
                    hours_to_interval_label(float(sch.get("interval_hours", 6)), mode=mode),
                )
            if hasattr(self, "sch_items_slider"):
                raw = int(sch.get("max_items", 100))
                raw = max(0, min(SCHEDULER_MAX_ITEMS, raw))
                self.sch_items_slider.set(float(raw))
                self._on_sch_items_changed(raw)
            from app.filter_utils import normalize_filter_value

            adv = normalize_filter_value(sch.get("advertiser_filter", "all"))
            self._sch_advertiser_filter.set(adv)
            if sch.get("download_images") and hasattr(self, "sch_download_images_cb"):
                self.sch_download_images_cb.select()
            if hasattr(self, "_sch_upload_var"):
                self._sch_upload_var.set(bool(sch.get("upload_to_platform", True)))
            if hasattr(self, "_sch_output_format"):
                fmt = sch.get("output_format") or "excel"
                if fmt not in ("excel", "csv", "json"):
                    fmt = "excel"
                self._sch_output_format.set(fmt)
                for val, btn in getattr(self, "_sch_format_btns", {}).items():
                    active = val == fmt
                    btn.configure(
                        fg_color=COLORS["primary"] if active else "transparent",
                        text_color=COLORS["accent_text"] if active else COLORS["text_secondary"],
                    )
            if hasattr(self, "sch_search_entry"):
                self.sch_search_entry.delete(0, "end")
                q = str(sch.get("search_query") or "")
                if q:
                    self.sch_search_entry.insert(0, q)
            if hasattr(self, "_sch_run_now_var"):
                self._sch_run_now_var.set(bool(sch.get("run_immediately", True)))
            if sch.get("enabled"):
                self._sch_expanded.set(True)
                self._toggle_sch()
            self._update_schedule_summary()
        except Exception:
            pass
        if sch.get("enabled") and sch.get("city"):
            self.after(2000, self._scheduler_resume)

    def _scheduler_resume(self) -> None:
        if not self._require_valid_license(show_message=False, switch_tab=False):
            return
        sch = self._settings.get("scheduler") or {}
        if not sch.get("city"):
            return
        self._scheduler_running = True
        self._scheduler.resume(sch.get("interval_hours", 6))
        self._emit("زمان‌بندی خودکار از سر گرفته شد.", "info")

    def _scheduler_save(self) -> None:
        sch = self._collect_scheduler_settings()
        sch["enabled"] = bool(self._scheduler.is_running)
        self._settings["scheduler"] = sch
        self._storage.save_settings(self._settings)
        self._emit("تنظیمات زمان‌بندی ذخیره شد.", "success")

    def _scheduler_play(self) -> None:
        if not self._require_valid_license():
            return
        if not self._execution.is_idle:
            messagebox.showwarning("تداخل", "یک عملیات استخراج در حال اجراست.")
            return
        sch = self._collect_scheduler_settings()
        if not sch.get("city"):
            messagebox.showwarning("زمان‌بندی", "لطفاً شهر را در بخش زمان‌بندی انتخاب کنید.")
            return
        mode = sch.get("mode") if sch.get("mode") in ("single", "batch") else "single"
        if mode == "batch":
            jobs = []
            if hasattr(self, "_sch_batch_panel"):
                jobs = self._sch_batch_panel.selected_jobs()
            if not jobs:
                messagebox.showwarning("زمان‌بندی گروهی", "حداقل یک زیردسته برای حالت گروهی انتخاب کنید.")
                return
            sch["interval_hours"] = clamp_interval_for_mode(
                float(sch.get("interval_hours") or 6), mode="batch",
            )
        elif not sch.get("subcategory") and not sch.get("transaction_type"):
            messagebox.showwarning("زمان‌بندی", "نوع معامله و زیردسته را انتخاب کنید.")
            return
        sch["enabled"] = True
        self._settings["scheduler"] = sch
        self._storage.save_settings(self._settings)
        self._scheduler_running = True
        interval = float(sch.get("interval_hours") or 6)
        if sch.get("run_immediately", True):
            self._scheduler.start(interval)
            self._emit("زمان‌بندی خودکار شروع شد — اجرای فوری.", "info")
        else:
            self._scheduler.resume(interval)
            self._emit("زمان‌بندی شروع شد — اجرای اول پس از بازهٔ انتخابی.", "info")
        self._update_schedule_summary()
        self._refresh_scheduler_live_banner()
        self._notifier.scheduler_started(
            interval_label=self.sch_interval_cb.get() if hasattr(self, "sch_interval_cb") else "",
            city=str(sch.get("city") or ""),
            max_items=int(sch.get("max_items") or 0),
        )
        self._sync_tray_status()
        Toast.show(
            self,
            "زمان‌بندی روشن شد — جزئیات هدف در بنر بالا قابل مشاهده است",
            tone="success",
        )

    def _scheduler_stop(self) -> None:
        self._scheduler_running = False
        self._scheduler.stop()
        sch = self._settings.get("scheduler") or {}
        sch["enabled"] = False
        self._settings["scheduler"] = sch
        self._storage.save_settings(self._settings)
        self._emit("زمان‌بندی خودکار متوقف شد.", "warning")
        self._notifier.scheduler_stopped()
        self._sync_tray_status()
        self._refresh_scheduler_live_banner()

    def _scheduler_resolve_batch_jobs(self, sch: Dict[str, Any]) -> list:
        if hasattr(self, "_sch_batch_panel"):
            jobs = self._sch_batch_panel.selected_jobs()
            if jobs:
                return jobs
        keys = sch.get("batch_job_keys") or []
        if keys:
            from app.category_jobs import iter_subcategory_jobs

            key_set = set()
            for item in keys:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    key_set.add((str(item[0]), str(item[1])))
            return iter_subcategory_jobs(selected_job_keys=key_set)
        from app.category_jobs import iter_subcategory_jobs

        return iter_subcategory_jobs()

    def _scheduler_fire(self) -> None:
        if not self._require_valid_license():
            self._scheduler_stop()
            return
        if not self._execution.is_idle:
            self._emit("زمان‌بندی: عملیات دیگری در حال اجراست — اجرای بعدی برنامه‌ریزی می‌شود.", "warning")
            self._record_scheduler_run(
                status="skipped",
                settings=self._get_scheduler_run_config(),
                error_message="عملیات دیگری در حال اجرا بود",
            )
            if self._scheduler.is_running:
                self._scheduler.on_extraction_finished()
            self._refresh_scheduler_live_banner()
            return
        if self._worker and self._worker.is_alive():
            self._emit("زمان‌بندی: استخراج قبلی هنوز در حال اجراست — اجرای بعدی به‌موقع برنامه‌ریزی می‌شود.", "warning")
            self._record_scheduler_run(
                status="skipped",
                settings=self._get_scheduler_run_config(),
                error_message="استخراج قبلی هنوز در حال اجرا بود",
            )
            if self._scheduler.is_running:
                self._scheduler.on_extraction_finished()
            self._refresh_scheduler_live_banner()
            return

        sch = self._get_scheduler_run_config()
        settings = self._scheduler_settings_to_run(sch)
        mode = settings.get("mode") if settings.get("mode") in ("single", "batch") else "single"
        self._settings["scheduler"] = sch
        self._storage.save_settings(self._settings)

        if not settings.get("city"):
            self._emit("زمان‌بندی: شهر مشخص نیست.", "error")
            self._notifier.extraction_failed("شهر در تنظیمات زمان‌بندی مشخص نیست.", scheduled=True)
            self._record_scheduler_run(
                status="failed",
                settings=sch,
                error_message="شهر در تنظیمات زمان‌بندی مشخص نیست",
            )
            self._scheduler_stop()
            return

        if mode == "batch":
            jobs = self._scheduler_resolve_batch_jobs(sch)
            if not jobs:
                self._record_scheduler_run(
                    status="failed",
                    settings=sch,
                    error_message="هیچ زیردسته‌ای برای استخراج گروهی انتخاب نشده",
                )
                self._scheduler_stop()
                return
            if not self._execution.try_start(ExecutionState.RUNNING_BATCH):
                self._record_scheduler_run(
                    status="skipped",
                    settings=sch,
                    error_message="شروع استخراج گروهی ممکن نبود",
                )
                if self._scheduler.is_running:
                    self._scheduler.on_extraction_finished()
                return
            self._reset_run_tracking(scheduled=True)
            self._last_run_settings = dict(settings)
            self._cancel_event.clear()
            self._batch_base_settings = dict(settings)
            self._batch_job_total = len(jobs)
            self._batch_job_index = 0
            self._active_batch_run = True
            self._pending_timeline_jobs = jobs
            self.progress.set(0)
            self.progress_percent.configure(text="۰٪")
            self._reset_stat_cards()
            self.scrape_start_time = time.time()
            if hasattr(self, "_scheduler"):
                self._scheduler.mark_run_started()
            self._append_log(
                f"شروع استخراج گروهی زمان‌بندی‌شده — {fa_digits(len(jobs))} زیردسته",
                "info",
            )
            self._set_extraction_ui_running(batch=True)
            self._set_status_message("استخراج گروهی زمان‌بندی‌شده…", tone="running")
            if hasattr(self, "current_task_lbl"):
                self.current_task_lbl.configure(text="استخراج گروهی زمان‌بندی‌شده…")
            self._notifier.extraction_started(
                city=str(settings.get("city") or ""),
                transaction=f"گروهی · {fa_digits(len(jobs))} زیردسته",
                max_items=int(settings.get("max_items") or 0),
                scheduled=True,
            )
            self._refresh_scheduler_live_banner()
            self._worker = threading.Thread(
                target=self._run_batch_thread,
                args=(settings, jobs),
                daemon=True,
            )
            self._worker.start()
            return

        if not self._execution.try_start(ExecutionState.RUNNING_SINGLE):
            self._record_scheduler_run(
                status="skipped",
                settings=sch,
                error_message="شروع استخراج ممکن نبود",
            )
            if self._scheduler.is_running:
                self._scheduler.on_extraction_finished()
            return

        self._reset_run_tracking(scheduled=True)
        self._last_run_settings = dict(settings)
        self._cancel_event.clear()
        self.progress.set(0)
        self.progress_percent.configure(text="۰٪")
        self._reset_stat_cards()
        self.scrape_start_time = time.time()
        if hasattr(self, "_scheduler"):
            self._scheduler.mark_run_started()
        self._append_log("شروع استخراج زمان‌بندی‌شده...", "info")
        self._set_extraction_ui_running(batch=False)
        self._set_status_message("استخراج زمان‌بندی‌شده…", tone="running")
        if hasattr(self, "current_task_lbl"):
            self.current_task_lbl.configure(text="استخراج زمان‌بندی‌شده…")
        self._notifier.extraction_started(
            city=str(settings.get("city") or ""),
            transaction=str(settings.get("transaction_type") or ""),
            max_items=int(settings.get("max_items") or 0),
            scheduled=True,
        )
        self._refresh_scheduler_live_banner()
        self._worker = threading.Thread(
            target=self._run_scrape_thread, args=(settings,), daemon=True,
        )
        self._worker.start()

    def _scheduler_status_update(self, text: str) -> None:
        running = bool(getattr(self, "_scheduler", None) and self._scheduler.is_running)
        if hasattr(self, "sch_status_lbl"):
            # داشبورد فقط وضعیت کوتاه نشان می‌دهد؛ جزئیات در متریک‌هاست
            short = "فعال" if running else "متوقف"
            if running and "در حال اجرا" in text:
                short = "در حال اجرا"
            self.sch_status_lbl.configure(text=short)
            try:
                self.sch_status_lbl.configure(
                    text_color=COLORS["success"] if running else COLORS["text_primary"],
                )
            except Exception:
                pass
        if hasattr(self, "_sch_footer_status"):
            self._sch_footer_status.configure(text="فعال" if running else "آماده شروع")
        if hasattr(self, "_sch_footer_dot"):
            self._sch_footer_dot.configure(
                fg_color=COLORS["success"] if running else COLORS["text_muted"],
            )
        if hasattr(self, "_sch_stat_next"):
            nxt = getattr(self._scheduler, "next_run_at", None) if hasattr(self, "_scheduler") else None
            if running and nxt:
                self._sch_stat_next.configure(text=format_timestamp_fa(nxt))
            elif running:
                self._sch_stat_next.configure(text="در حال اجرا")
            else:
                self._sch_stat_next.configure(text="—")
        if hasattr(self, "_sch_stat_remain"):
            rem = getattr(self._scheduler, "remaining_seconds", None) if hasattr(self, "_scheduler") else None
            if rem is None:
                self._sch_stat_remain.configure(text="—" if not running else "اکنون")
            else:
                self._sch_stat_remain.configure(text=format_duration_fa(rem, style="words"))
        if hasattr(self, "_sch_stat_last") and hasattr(self, "_scheduler"):
            last = self._scheduler.last_run_at
            if last:
                self._sch_stat_last.configure(text=format_timestamp_fa(last))
            else:
                self._sch_stat_last.configure(text="—")
        if hasattr(self, "_sch_stat_count"):
            try:
                stats = self._storage.scheduler_run_stats()
                self._sch_stat_count.configure(text=fa_digits(stats.get("total") or 0))
            except Exception:
                if hasattr(self, "_scheduler"):
                    self._sch_stat_count.configure(text=fa_digits(self._scheduler.run_count))
        self._update_schedule_summary()
        self._refresh_scheduler_live_banner()

    def _record_scheduler_run(
        self,
        *,
        status: str,
        settings: Optional[Dict[str, Any]] = None,
        output_path: str = "",
        ok_count: int = 0,
        total_posts: int = 0,
        duration_seconds: int = 0,
        error_message: str = "",
    ) -> None:
        settings = settings or {}
        filters = settings.get("filters") if isinstance(settings.get("filters"), dict) else {}
        finished_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
        # فقط وقتی استخراج واقعی شروع شده، زمان شروع scrape را استفاده کن
        if status not in ("skipped",) and self.scrape_start_time:
            started_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.scrape_start_time))
        else:
            started_iso = finished_iso
            duration_seconds = 0
        try:
            self._storage.add_scheduler_run(
                {
                    "started_at": started_iso,
                    "finished_at": finished_iso,
                    "status": status,
                    "province": settings.get("province") or "",
                    "city": settings.get("city") or "",
                    "district": settings.get("district") or "",
                    "transaction_type": settings.get("transaction_type") or "",
                    "subcategory": settings.get("subcategory") or "",
                    "search_query": settings.get("search_query") or filters.get("search_query") or "",
                    "max_items": int(settings.get("max_items") or 0),
                    "output_format": settings.get("output_format") or "",
                    "output_path": output_path or "",
                    "total_posts": int(total_posts or 0),
                    "ok_count": int(ok_count or 0),
                    "duration_seconds": int(duration_seconds or 0),
                    "error_message": error_message or "",
                    "advertiser_filter": (
                        settings.get("advertiser_filter")
                        or filters.get("advertiser_filter")
                        or ""
                    ),
                    "mode": str(settings.get("mode") or "single"),
                    "jobs_total": int(settings.get("jobs_total") or 0),
                    "jobs_success": int(settings.get("jobs_success") or 0),
                    "jobs_failed": int(settings.get("jobs_failed") or 0),
                }
            )
        except Exception as exc:
            self._storage.append_log(f"SCHEDULER HISTORY ERR: {exc}")
            self._emit(f"ثبت تاریخچه زمان‌بندی ناموفق: {exc}", "error")
        self.after(50, self._refresh_scheduler_history)
        self.after(60, self._refresh_scheduler_live_banner)

    def _record_scheduler_batch_run(self, summary: BatchRunSummary) -> None:
        settings = dict(self._last_run_settings or self._get_scheduler_run_config())
        duration_seconds = 0
        if self.scrape_start_time:
            duration_seconds = int(time.time() - self.scrape_start_time)
        ok = int(summary.success_count)
        fail = int(summary.failed_count)
        total_jobs = int(summary.total_jobs or (ok + fail))
        extracted = sum(int(getattr(r, "extracted_count", 0) or 0) for r in summary.results)
        if summary.cancelled:
            status = "cancelled"
        elif fail and not ok:
            status = "failed"
        elif fail:
            status = "success"  # جزئی موفق — در تاریخچه با jobs_failed مشخص می‌شود
        elif ok:
            status = "success"
        else:
            status = "no_results"
        settings["mode"] = "batch"
        settings["jobs_total"] = total_jobs
        settings["jobs_success"] = ok
        settings["jobs_failed"] = fail
        settings["subcategory"] = f"گروهی · {fa_digits(total_jobs)} زیردسته"
        settings["transaction_type"] = settings.get("transaction_type") or "استخراج گروهی"
        err = ""
        if fail:
            err = f"{fa_digits(fail)} زیردسته نیازمند توجه"
        self._record_scheduler_run(
            status=status,
            settings=settings,
            output_path="",
            ok_count=extracted,
            total_posts=extracted,
            duration_seconds=duration_seconds,
            error_message=err,
        )

    def _refresh_scheduler_history(self) -> None:
        if not hasattr(self, "_sch_history"):
            return
        try:
            runs = self._storage.list_scheduler_runs(limit=80)
            self._sch_history.set_runs(runs)
            if hasattr(self, "_sch_stat_count"):
                stats = self._storage.scheduler_run_stats()
                self._sch_stat_count.configure(text=fa_digits(stats.get("total") or 0))
            if hasattr(self, "_sch_stat_last") and runs:
                self._sch_stat_last.configure(
                    text=format_datetime_fa(str(runs[0].get("finished_at") or runs[0].get("started_at") or "")),
                )
        except Exception:
            pass

    def _clear_scheduler_history(self) -> None:
        if not messagebox.askyesno("پاک کردن تاریخچه", "همه گزارش‌های زمان‌بندی حذف شوند؟"):
            return
        try:
            self._storage.clear_scheduler_runs()
            self._refresh_scheduler_history()
            Toast.show(self, "تاریخچه زمان‌بندی پاک شد", tone="success")
        except Exception as exc:
            self._set_status_message(f"پاک کردن تاریخچه ناموفق: {exc}", tone="error")

    def _open_schedule_output(self, path: str) -> None:
        if not path:
            return
        target = path if os.path.exists(path) else os.path.dirname(path)
        if not target or not os.path.exists(target):
            Toast.show(self, "فایل خروجی پیدا نشد", tone="warning")
            return
        try:
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.run(["open", target], check=False)
            else:
                subprocess.run(["xdg-open", target], check=False)
        except Exception as exc:
            self._set_status_message(f"باز کردن خروجی ناموفق: {exc}", tone="error")

    def _update_path_preview(self) -> None:
        if not hasattr(self, "_path_preview"):
            return
        try:
            preview = ExtractionEngine.preview_output_structure(
                self._collect_settings(), self._places
            )
            self._path_preview.configure(text=f"مسیر خروجی: {preview}")
            self._sync_status_path()
            update_summary_chips(self)
        except Exception:
            self._path_preview.configure(text="")

    def _save_settings(self) -> None:
        self._settings["max_workers"] = int(round(float(self.workers_slider.get())))
        appearance = self._appearance_var.get()
        if appearance not in ("light", "dark", "system"):
            appearance = "light"
        self._settings["appearance"] = appearance
        ctk.set_appearance_mode(appearance)
        self._settings["output_format"] = self.output_format.get()
        self._settings["max_items"] = int(round(float(self.items_slider.get())))
        self._settings["download_images"] = bool(self.download_images_cb.get())
        self._settings["extraction"] = self._collect_settings()
        self._settings["notifications"] = self._collect_notification_settings()
        self._settings["tray"] = self._collect_tray_settings()
        # همگام‌سازی اعلان پایان/خطا با tray prefs
        self._settings["notifications"]["extraction"] = bool(
            self._settings["tray"].get("notify_extraction_complete", True)
        )
        self._settings["notifications"]["errors"] = bool(
            self._settings["tray"].get("notify_errors", True)
        )
        self._storage.save_settings(self._settings)
        self._license.api_base_url = DEFAULT_LICENSE_API_URL.rstrip("/")
        self._set_status_message("تنظیمات ذخیره شد", tone="success")
        Toast.show(self, "تنظیمات با موفقیت ذخیره شد", tone="success")

    def _save_extraction_settings(self) -> None:
        self._settings["extraction"] = self._collect_settings()
        self._storage.save_settings(self._settings)

    # ── License ─────────────────────────────────────────────────────────
    def _run_on_ui_thread(self, fn: Callable[[], None]) -> None:
        """اجرای callback روی main thread — امن برای thread پس‌زمینه."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if threading.current_thread() is threading.main_thread():
            try:
                fn()
            except Exception:
                pass
            return
        self._ui_callbacks.put(fn)

    def _wire_account_login_panel(self) -> None:
        card = getattr(self, "_account_login_card", None)
        if not card:
            return
        card._login_btn.configure(command=self._account_login_and_bind)
        card._logout_btn.configure(command=self._account_logout)
        self._sync_account_login_fields()

    def _sync_account_login_fields(self) -> None:
        card = getattr(self, "_account_login_card", None)
        if not card:
            return
        logged_in = self._desktop_auth.has_session()
        set_account_session_visible(card, logged_in)
        if not logged_in:
            return
        username, password = self._desktop_auth.get_saved_login()
        if not username:
            info = self._license.get_license_info() or {}
            account = info.get("account") or {}
            allocation = info.get("allocation") or {}
            if allocation.get("is_assigned"):
                username = (account.get("phone") or "").strip()
            else:
                username = (
                    (account.get("phone") or "").strip()
                    or (account.get("display_name") or "").strip()
                )
        set_account_login_fields(card, username=username, password=password)

    def _refresh_license_from_desktop_session(self) -> bool:
        """پروفایل و allocation را از API حساب — نه validate قدیمی — بگیرد."""
        if not self._desktop_auth.has_session():
            return False
        if not self._desktop_auth.ensure_access_token():
            return False
        try:
            hw = self._license.get_hardware_fingerprint()
            info = self._license.get_license_info() or {}
            license_key = info.get("license_key")
            session = self._desktop_auth.validate_session(
                hw, license_key=license_key,
            )
        except DesktopAuthError:
            return False
        except Exception:
            return False
        key = session.get("license_key") or license_key
        if not key:
            return False
        self._license.apply_bind_payload(session, key)
        return True

    def _persist_login_fields_from_card(self) -> None:
        card = getattr(self, "_account_login_card", None)
        if not card or not self._desktop_auth.has_session():
            return
        username = card._login_user.get().strip()
        password = card._login_pass.get()
        if username or password:
            self._desktop_auth.save_login_credentials(username, password)

    def _account_logout(self) -> None:
        if not messagebox.askyesno(
            "خروج",
            "از حساب خارج شوید؟\n\n"
            "لایسنس این دستگاه غیرفعال می‌شود و تا ورود مجدد امکان استخراج ندارید.",
        ):
            return

        card = getattr(self, "_account_login_card", None)
        if card:
            set_account_login_busy(card, True)

        def _worker() -> None:
            warn = ""
            try:
                result = self._license.deactivate_or_clear_local()
                if not result.get("success"):
                    warn = result.get("error") or "غیرفعال‌سازی ناموفق بود."
            except Exception as exc:
                self._license.release_local_license()
                warn = str(exc)
            try:
                self._desktop_auth.logout()
            except Exception:
                pass
            self._desktop_account_refresh_done = False

            def _ui() -> None:
                self.license_validated = False
                if hasattr(self, "license_key_entry"):
                    self.license_key_entry.delete(0, "end")
                self._update_license_ui()
                if card:
                    set_account_session_visible(card, False)
                    set_account_login_error(card, "")
                    set_account_login_busy(card, False)
                    set_account_login_fields(card)
                self._switch_tab("license")
                if warn:
                    Toast.show(
                        self,
                        f"از حساب خارج شدید — {warn}",
                        tone="warning",
                    )
                else:
                    Toast.show(self, "از حساب و لایسنس این دستگاه خارج شدید", tone="info")

            self._run_on_ui_thread(_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def _account_login_and_bind(self) -> None:
        card = getattr(self, "_account_login_card", None)
        if not card:
            return
        username = card._login_user.get().strip()
        password = card._login_pass.get()
        if not username or not password:
            set_account_login_error(card, "شماره موبایل و رمز عبور را وارد کنید.")
            return
        set_account_login_error(card, "")
        set_account_login_busy(card, True)

        def _worker() -> None:
            try:
                self._desktop_auth.login(username, password)
                hw = self._license.get_hardware_fingerprint()
                try:
                    bind_data = self._desktop_auth.bind(hw)
                except DesktopAuthError as exc:
                    if exc.code != "LICENSE_SELECTION_REQUIRED":
                        raise
                    licenses = (exc.fields or {}).get("licenses") or []
                    if not licenses:
                        eligible = self._desktop_auth.get_eligible(hw)
                        licenses = [
                            x for x in eligible.get("licenses", []) if x.get("can_bind")
                        ]
                    self._run_on_ui_thread(lambda: self._prompt_license_selection(licenses, hw))
                    return
                self._run_on_ui_thread(lambda data=bind_data: self._finish_account_bind(data))
            except DesktopAuthError as exc:
                err_msg = exc.message
                self._run_on_ui_thread(lambda msg=err_msg: self._account_login_failed(msg))
            except Exception as exc:
                err_msg = str(exc)
                self._run_on_ui_thread(lambda msg=err_msg: self._account_login_failed(msg))
            finally:
                self._run_on_ui_thread(lambda: set_account_login_busy(card, False))

        threading.Thread(target=_worker, daemon=True).start()

    def _prompt_license_selection(self, licenses: list, hw: str) -> None:
        card = getattr(self, "_account_login_card", None)
        if card:
            set_account_login_busy(card, False)

        bindable = [x for x in licenses if x.get("can_bind", True)]
        if not bindable:
            self._account_login_failed("لایسنس قابل اتصال یافت نشد.")
            return

        def _chosen(license_id: int) -> None:
            if card:
                set_account_login_busy(card, True)

            def _bind() -> None:
                try:
                    data = self._desktop_auth.bind(hw, license_id=license_id)
                    self._run_on_ui_thread(lambda d=data: self._finish_account_bind(d))
                except DesktopAuthError as exc:
                    err_msg = exc.message
                    self._run_on_ui_thread(lambda msg=err_msg: self._account_login_failed(msg))
                finally:
                    if card:
                        self._run_on_ui_thread(lambda: set_account_login_busy(card, False))

            threading.Thread(target=_bind, daemon=True).start()

        LicenseSelectionDialog(self, bindable, on_select=_chosen)

    def _account_login_failed(self, message: str) -> None:
        card = getattr(self, "_account_login_card", None)
        if card:
            set_account_login_error(card, message)
        self._notifier.license_invalid(message)

    def _finish_account_bind(self, bind_data: Dict[str, Any]) -> None:
        license_key = bind_data.get("license_key") or ""
        if not license_key:
            self._account_login_failed("پاسخ سرور ناقص بود.")
            return
        self._license.apply_bind_payload(bind_data, license_key)
        self.license_validated = True
        self._desktop_account_refresh_done = False
        self._persist_login_fields_from_card()
        self._update_license_ui()
        self._report_first_launch_if_needed()
        card = getattr(self, "_account_login_card", None)
        if card:
            set_account_login_error(card, "")
            self._persist_login_fields_from_card()
            self._sync_account_login_fields()
        plan = bind_data.get("plan_name") or ""
        self._notifier.license_activated(plan_name=str(plan))
        Toast.show(self, "لایسنس با ورود حساب فعال شد", tone="success")
        self._switch_tab("extract")

    def _try_account_session_recovery(self) -> bool:
        if not self._desktop_auth.has_session():
            return False
        try:
            if not self._desktop_auth.ensure_access_token():
                return False
            hw = self._license.get_hardware_fingerprint()
            info = self._license.get_license_info()
            license_key = (info or {}).get("license_key")
            try:
                session = self._desktop_auth.validate_session(hw, license_key=license_key)
            except DesktopAuthError:
                eligible = self._desktop_auth.get_eligible(hw)
                auto_id = eligible.get("auto_bind_license_id")
                if auto_id:
                    session = self._desktop_auth.bind(hw, license_id=auto_id)
                else:
                    bindable = [x for x in eligible.get("licenses", []) if x.get("can_bind")]
                    if len(bindable) == 1:
                        session = self._desktop_auth.bind(hw, license_id=bindable[0]["license_id"])
                    else:
                        return False
            key = session.get("license_key") or license_key
            if key:
                self._license.apply_bind_payload(session, key)
            result = self._license.validate_license(
                force_check=True,
                keep_account_fields=True,
            )
            return self._apply_license_validation(result, switch_tab=False)
        except Exception:
            return False

    def _apply_license_validation(
        self,
        result: Dict[str, Any],
        *,
        show_message: bool = False,
        switch_tab: bool = False,
    ) -> bool:
        """به‌روزرسانی وضعیت لایسنس از نتیجه اعتبارسنجی."""
        valid = bool(result.get("valid"))
        self.license_validated = valid
        self._update_license_ui()
        if valid:
            return True
        err = result.get("error", "لایسنس معتبر نیست")
        if show_message:
            self._notifier.license_invalid(err)
            messagebox.showwarning(
                "لایسنس",
                f"{err}\n\nلطفاً لایسنس را فعال یا تمدید کنید.",
            )
        if switch_tab:
            self._switch_tab("license")
        return False

    def _require_valid_license(
        self,
        *,
        show_message: bool = True,
        switch_tab: bool = True,
        force_check: bool = False,
    ) -> bool:
        """اعتبارسنجی لحظه‌ای قبل از عملیات — انقضا در همان جلسه هم اعمال می‌شود."""
        result = self._license.validate_license(
            force_check=force_check,
            keep_account_fields=self._desktop_auth.has_session(),
        )
        return self._apply_license_validation(
            result,
            show_message=show_message,
            switch_tab=switch_tab,
        )

    def _check_license_on_startup(self) -> None:
        has_session = self._desktop_auth.has_session()
        result = self._license.validate_license(
            force_check=False,
            keep_account_fields=has_session,
        )
        if self._apply_license_validation(result, switch_tab=False):
            self._report_first_launch_if_needed()
            if has_session:
                self._schedule_desktop_account_refresh()
            card = getattr(self, "_account_login_card", None)
            if card:
                self._sync_account_login_fields()
            return

        if self._try_account_session_recovery():
            self._report_first_launch_if_needed()
            self._schedule_desktop_account_refresh()
            card = getattr(self, "_account_login_card", None)
            if card:
                self._sync_account_login_fields()
            return

        err = result.get("error", "لایسنس معتبر نیست")
        if not self._desktop_auth.has_session():
            self._notifier.license_invalid(err)
            self.after(
                300,
                lambda: messagebox.showinfo(
                    "فعال‌سازی",
                    f"{err}\n\nمی‌توانید با حساب کاربری (موبایل و رمز) وارد شوید "
                    "یا کلید لایسنس را وارد کنید.",
                ),
            )
        card = getattr(self, "_account_login_card", None)
        if card:
            self._sync_account_login_fields()

    def _report_first_launch_if_needed(self) -> None:
        def _run() -> None:
            try:
                self._license.report_client_event('first_launch', app_version=APP_VERSION)
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

    def _update_allocation_strip(self, allocation: Optional[Dict[str, Any]]) -> None:
        strip = getattr(self, "_license_allocation_strip", None)
        if not strip:
            return
        if not allocation or not allocation.get("is_assigned"):
            strip.grid_remove()
            return

        by_name = (allocation.get("assigned_by_name") or "").strip()
        by_phone = (allocation.get("assigned_by_phone") or "").strip()
        owner_name = (allocation.get("owner_name") or "").strip()

        if by_name:
            self._license_allocation_lbl.configure(text=f"تخصیص‌یافته توسط {by_name}")
        else:
            self._license_allocation_lbl.configure(
                text="این لایسنس توسط آژانس به شما تخصیص داده شده است.",
            )

        hint_parts = []
        if by_phone:
            hint_parts.append(by_phone)
        if owner_name and owner_name != by_name:
            hint_parts.append(f"آژانس {owner_name}")
        assigned_at = allocation.get("assigned_at")
        if assigned_at:
            hint_parts.append(format_datetime_fa(assigned_at))
        hint = " · ".join(hint_parts)
        if hint:
            self._license_allocation_hint.configure(text=hint)
            if not self._license_allocation_hint.winfo_ismapped():
                self._license_allocation_hint.pack(anchor="e", pady=(1, 0))
        else:
            self._license_allocation_hint.configure(text="")
            self._license_allocation_hint.pack_forget()

        strip.grid(row=2, column=0, sticky="ew", pady=(0, SPACE_SM))

    def _account_profile_stale(self, info: Optional[Dict[str, Any]]) -> bool:
        if not info or not self._desktop_auth.has_session():
            return False
        allocation = info.get("allocation") or {}
        if not allocation.get("is_assigned"):
            return False
        account = info.get("account") or {}
        owner_phone = (allocation.get("assigned_by_phone") or "").strip()
        account_phone = (account.get("phone") or "").strip()
        if owner_phone and account_phone and account_phone == owner_phone:
            return True
        role = str(account.get("role") or "").strip()
        return role in ("مالک", "owner", "Owner")

    def _schedule_desktop_account_refresh(self) -> None:
        if getattr(self, "_desktop_account_refresh_running", False):
            return
        if getattr(self, "_desktop_account_refresh_done", False):
            return
        self._desktop_account_refresh_running = True

        def _worker() -> None:
            try:
                self._refresh_license_from_desktop_session()
                self._run_on_ui_thread(self._update_license_ui)
            finally:
                self._desktop_account_refresh_running = False
                self._desktop_account_refresh_done = True

        threading.Thread(target=_worker, daemon=True).start()

    def _update_license_ui(self) -> None:
        info = self._license.get_license_info()
        if info and self._account_profile_stale(info):
            self._schedule_desktop_account_refresh()
        if info and self.license_validated:
            self.license_banner.configure(
                fg_color=COLORS["success_bg"],
                border_color=COLORS["success_border"],
            )
            self.license_status_lbl.configure(
                text="✓  لایسنس فعال و معتبر است",
                text_color=COLORS["success"],
            )
            if hasattr(self, "_license_status_dot"):
                self._license_status_dot.configure(fg_color=COLORS["success"])
            plan_name = info.get("plan_name") or "نامشخص"
            self.license_status_hint.configure(
                text=f"پلن «{plan_name}» — دسترسی کامل به استخراج فعال است.",
            )
            key = info.get("license_key", "")
            if hasattr(self, "license_key_entry"):
                self.license_key_entry.delete(0, "end")
                self.license_key_entry.insert(0, key)

            max_dev = info.get("max_activations")
            self._plan_name_lbl.configure(text=plan_name)
            self._plan_status_lbl.configure(text="فعال", text_color=COLORS["success"])
            self._plan_key_lbl.configure(text=key or "—")
            self._plan_activated_lbl.configure(
                text=format_datetime_fa(info.get("activated_at")),
            )
            self._plan_expiry_lbl.configure(
                text=format_expiry_fa(info.get("expires_at")),
            )
            self._plan_devices_lbl.configure(
                text=fa_digits(max_dev) if max_dev else "۱",
            )
            if hasattr(self, "_plan_days_lbl"):
                days_txt = "—"
                expires = info.get("expires_at")
                if expires:
                    try:
                        from datetime import datetime, timezone
                        exp = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                        now = datetime.now(timezone.utc)
                        delta = (exp - now).days
                        days_txt = fa_digits(max(0, delta))
                    except Exception:
                        days_txt = "—"
                self._plan_days_lbl.configure(text=days_txt)
            allocation = info.get("allocation") or {}
            self._update_allocation_strip(allocation)
            if hasattr(self, "_plan_empty"):
                self._plan_empty.pack_forget()
            if hasattr(self, "_plan_body") and not self._plan_body.winfo_ismapped():
                self._plan_body.pack(fill="both", expand=True, padx=SPACE_MD, pady=(0, SPACE_MD))
            if hasattr(self, "license_account_card"):
                update_license_account_panel(self.license_account_card, info.get("account"))
            if hasattr(self, "_stat_license"):
                self._stat_license.set_value("فعال", tone="success")
            if hasattr(self, "_header"):
                self._header.chip_license.set_value("فعال", tone="success")
            self._check_license_expiry_notice(info)
            self._sync_account_login_fields()
        else:
            self.license_banner.configure(
                fg_color=COLORS["error_bg"],
                border_color=COLORS["error_border"],
            )
            self.license_status_lbl.configure(
                text="!  لایسنس فعال نیست",
                text_color=COLORS["error"],
            )
            if hasattr(self, "_license_status_dot"):
                self._license_status_dot.configure(fg_color=COLORS["error"])
            self.license_status_hint.configure(
                text="با ورود حساب یا کلید لایسنس، دسترسی را فعال کنید.",
            )
            if hasattr(self, "_plan_body"):
                self._plan_body.pack_forget()
            self._update_allocation_strip(None)
            if hasattr(self, "_plan_empty") and not self._plan_empty.winfo_ismapped():
                self._plan_empty.pack(anchor="e", padx=SPACE_MD, pady=(0, SPACE_MD))
            if hasattr(self, "license_account_card"):
                update_license_account_panel(self.license_account_card, None)
            if hasattr(self, "_stat_license"):
                self._stat_license.set_value("غیرفعال", tone="error")
            if hasattr(self, "_header"):
                self._header.chip_license.set_value("غیرفعال", tone="error")

    def _copy_hardware_id(self) -> None:
        hw_id = getattr(self, "hw_id_value", "") or self._license.get_hardware_fingerprint()
        try:
            self.clipboard_clear()
            self.clipboard_append(hw_id)
            self.update()
            self._set_status_message("شناسه سخت‌افزاری کپی شد.", tone="success")
        except Exception:
            messagebox.showerror("خطا", "کپی شناسه ممکن نشد. متن را انتخاب و Ctrl+C بزنید.")

    def _activate_license(self) -> None:
        key = self.license_key_entry.get().strip()
        if not key:
            messagebox.showwarning("لایسنس", "کلید لایسنس را وارد کنید.")
            return
        result = self._license.activate_license(key)
        if result.get("success"):
            self.license_validated = True
            self._update_license_ui()
            self._report_first_launch_if_needed()
            plan = result.get("plan_name") or ""
            self._notifier.license_activated(plan_name=str(plan))
            messagebox.showinfo("لایسنس", result.get("message", "فعال شد."))
        else:
            self._notifier.license_invalid(result.get("error", "خطا"))
            messagebox.showerror("لایسنس", result.get("error", "خطا"))

    def _validate_license(self) -> None:
        has_session = self._desktop_auth.has_session()
        self._desktop_account_refresh_done = False
        if has_session:
            refreshed = self._refresh_license_from_desktop_session()
            if refreshed:
                self.license_validated = True
                self._update_license_ui()
                self._set_status_message("لایسنس و پروفایل به‌روز شد.", tone="success")
                return
        result = self._license.validate_license(
            force_check=True,
            keep_account_fields=has_session,
        )
        if has_session:
            self._refresh_license_from_desktop_session()
        self.license_validated = bool(result.get("valid"))
        self._update_license_ui()
        if self.license_validated:
            messagebox.showinfo("لایسنس", result.get("message", "معتبر است."))
        else:
            self._notifier.license_invalid(result.get("error", "نامعتبر"))
            messagebox.showerror("لایسنس", result.get("error", "نامعتبر"))

    def _deactivate_license(self) -> None:
        if not messagebox.askyesno("لایسنس", "لایسنس غیرفعال شود؟"):
            return
        result = self._license.deactivate_license()
        self.license_validated = False
        self._update_license_ui()
        if result.get("success"):
            self._notifier.license_deactivated()
            messagebox.showinfo("لایسنس", "غیرفعال شد.")
        else:
            messagebox.showerror("لایسنس", result.get("error", "خطا"))

    # ── Extraction ──────────────────────────────────────────────────────
    def _require_idle_execution(self, action_label: str) -> bool:
        if self._execution.is_idle:
            return True
        if self._execution.state == ExecutionState.CANCELLING:
            messagebox.showinfo("در حال لغو", "عملیات قبلی در حال لغو است. لطفاً چند لحظه صبر کنید.")
        else:
            messagebox.showinfo("در حال اجرا", f"یک عملیات استخراج در حال اجراست — {action_label} ممکن نیست.")
        return False

    def _on_extraction_mode_changed(self, mode: str) -> None:
        self._extraction_mode = mode if mode in ("single", "batch") else "single"
        if hasattr(self, "_single_panel") and hasattr(self, "_batch_host"):
            if self._extraction_mode == "batch":
                self._single_panel.pack_forget()
                self._batch_host.pack(fill="x")
                if hasattr(self, "_start_hint"):
                    self._start_hint.pack(anchor="e", padx=SPACE_SM, pady=(0, SPACE_SM))
            else:
                self._batch_host.pack_forget()
                self._single_panel.pack(fill="x")
                if hasattr(self, "_start_hint"):
                    self._start_hint.pack_forget()
        self._refresh_start_button_label()
        update_summary_chips(self)
        if hasattr(self, "_batch_panel"):
            self._batch_panel._update_summary()

    def _refresh_start_button_label(self) -> None:
        if not hasattr(self, "start_btn"):
            return
        if getattr(self, "_extraction_mode", "single") == "batch" and hasattr(self, "_batch_panel"):
            count = self._batch_panel.count_selected()
            self.start_btn.configure(text=f"شروع استخراج {fa_digits(count)} زیردسته")
        else:
            self.start_btn.configure(text="شروع استخراج")

    def _on_primary_extract(self) -> None:
        if getattr(self, "_extraction_mode", "single") == "batch":
            self._start_batch()
        else:
            self._start()

    def _set_extraction_ui_running(self, *, batch: bool = False) -> None:
        running_label = "در حال استخراج…"
        self.start_btn.configure(state="disabled", text=running_label)
        if hasattr(self, "_batch_panel"):
            self._batch_panel.set_enabled(False)
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.configure(state="normal")
        if hasattr(self, "_op_status_badge"):
            self._op_status_badge.configure_text("در حال اجرا", tone="brand")
        if hasattr(self, "_stat_extract"):
            self._stat_extract.set_value("در حال اجرا", tone="running")
        if hasattr(self, "_workspace"):
            self._workspace.show_running(batch=batch)
        if batch and hasattr(self, "_workspace"):
            # jobs ممکن است بعداً با set_jobs ست شوند؛ پیش‌فرض از پنل
            if hasattr(self, "_batch_panel") and not getattr(self, "_pending_timeline_jobs", None):
                self._workspace.timeline.set_jobs(self._batch_panel.selected_jobs())
            elif getattr(self, "_pending_timeline_jobs", None):
                self._workspace.timeline.set_jobs(self._pending_timeline_jobs)
                self._pending_timeline_jobs = None
        self._sync_tray_status()

    def _set_extraction_ui_idle(self) -> None:
        self.start_btn.configure(state="normal")
        self._refresh_start_button_label()
        if hasattr(self, "_batch_panel"):
            self._batch_panel.set_enabled(True)
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.configure(state="disabled")
        if hasattr(self, "_op_status_badge"):
            self._op_status_badge.configure_text("آماده", tone="muted")
        if hasattr(self, "_stat_extract"):
            self._stat_extract.set_value("آماده", tone="success")
        # workspace به idle برنمی‌گردد مگر صریح — completed جداگانه set می‌شود
        self._sync_tray_status()

    def _batch_progress_threadsafe(self, index: int, total: int, frac: float, label: str) -> None:
        safe_label = label.replace("|", "/")
        self._queue.put((f"__BATCH_PROGRESS__:{index}|{total}|{frac}|{safe_label}", "normal"))

    def _batch_job_complete_threadsafe(self, index: int, result: BatchJobResult) -> None:
        payload = json.dumps(result.to_dict(), ensure_ascii=False)
        self._queue.put((f"__BATCH_JOB_DONE__:{payload}", "normal"))

    def _build_batch_confirm_text(self, job_count: int, max_items: int) -> str:
        upload = "فعال" if self._upload_platform_var.get() else "غیرفعال"
        return (
            f"{fa_digits(job_count)} زیردسته انتخاب شده\n"
            f"حداکثر {fa_digits(max_items)} آگهی برای هر زیردسته\n"
            f"آپلود خودکار: {upload}\n"
            f"تخمین حداکثر: {fa_digits(job_count * max_items)} آگهی"
        )

    def _start_batch(self) -> None:
        if not self._require_valid_license():
            return
        if not self._require_idle_execution("استخراج دسته‌ای"):
            return
        if self._scheduler.is_running:
            messagebox.showwarning("تداخل", "زمان‌بندی خودکار فعال است. ابتدا آن را متوقف کنید.")
            return
        if not self.city_cb.get():
            messagebox.showwarning("هشدار", "لطفاً شهر را انتخاب کنید.")
            return
        if not hasattr(self, "_batch_panel"):
            return

        jobs = self._batch_panel.selected_jobs()
        if not jobs:
            messagebox.showwarning("انتخاب دسته", "حداقل یک زیردسته انتخاب کنید.")
            return

        base = self._collect_settings()
        job_count = len(jobs)
        max_items = int(base.get("max_items") or 0)
        parts = [
            p for p in (
                base.get("province") or "",
                base.get("city") or "",
                base.get("district") or "",
            )
            if p and p != "—"
        ]
        location = "، ".join(parts)
        BatchConfirmDialog(
            self,
            on_confirm=lambda: self._launch_batch(base, jobs),
            job_count=job_count,
            max_items=max_items,
            upload_enabled=bool(self._upload_platform_var.get()),
            location=location,
        )

    def _launch_batch(self, base_settings: Dict[str, Any], jobs: list) -> None:
        if not self._execution.try_start(ExecutionState.RUNNING_BATCH):
            messagebox.showinfo("در حال اجرا", "عملیات دیگری در حال اجراست.")
            return

        self._save_extraction_settings()
        self._reset_run_tracking(scheduled=False)
        self._cancel_event.clear()
        self._batch_base_settings = dict(base_settings)
        self._batch_job_total = len(jobs)
        self._batch_job_index = 0
        self._active_batch_run = True
        self._pending_timeline_jobs = jobs
        self.progress.set(0)
        self.progress_percent.configure(text="۰٪")
        self._reset_stat_cards()
        self.scrape_start_time = time.time()
        self._append_log(f"شروع استخراج دسته‌ای — {len(jobs)} زیردسته", "info")
        self._set_extraction_ui_running(batch=True)
        self._set_status_message("استخراج دسته‌ای…", tone="running")
        if hasattr(self, "current_task_lbl"):
            self.current_task_lbl.configure(text="آماده‌سازی batch…")

        self._worker = threading.Thread(
            target=self._run_batch_thread,
            args=(base_settings, jobs),
            daemon=True,
        )
        self._worker.start()

    def _run_batch_thread(self, base_settings: Dict[str, Any], jobs: list) -> None:
        try:
            summary = self._batch_runner.run(base_settings, jobs)
            self._batch_summary = summary
            self._queue.put(("__BATCH_DONE__", "normal"))
        except Exception as exc:
            self._emit_threadsafe(f"✗ خطای batch: {exc}", "error")
            self._storage.append_log(f"BATCH ERR: {exc}")
            self._queue.put(("__BATCH_DONE__", "error"))
        finally:
            self._queue.put(("__DONE__", "normal"))

    def _retry_failed_batch_jobs(self, failed_results: list) -> None:
        if not self._batch_base_settings:
            return
        specs = [
            BatchJobSpec(r.transaction_type, r.subcategory, r.api_slug)
            for r in failed_results
        ]
        jobs = [
            {"transaction_type": s.transaction_type, "subcategory": s.subcategory, "api_slug": s.api_slug}
            for s in specs
        ]
        if not jobs:
            return
        if not self._execution.try_start(ExecutionState.RUNNING_BATCH):
            messagebox.showinfo("در حال اجرا", "عملیات دیگری در حال اجراست.")
            return
        self._reset_run_tracking(scheduled=False)
        self._cancel_event.clear()
        self._batch_job_total = len(jobs)
        self._active_batch_run = True
        self._pending_timeline_jobs = jobs
        self._set_extraction_ui_running(batch=True)
        self._append_log(f"تلاش مجدد — {len(jobs)} job", "info")
        self._worker = threading.Thread(
            target=self._run_batch_thread,
            args=(self._batch_base_settings, jobs),
            daemon=True,
        )
        self._worker.start()

    def _update_batch_summary(self) -> None:
        if hasattr(self, "_batch_panel"):
            self._batch_panel._update_summary()

    def _run_single_job(self, settings: Dict[str, Any]) -> None:
        tx = str(settings.get("transaction_type") or "")
        sub = str(settings.get("subcategory") or "")
        api = resolve_api_slug(tx, sub) or ""
        job_settings = build_job_settings(
            settings,
            {"transaction_type": tx, "subcategory": sub, "api_slug": api},
        )
        result = self._job_service.run(
            job_settings,
            transaction_type=tx,
            subcategory=sub,
            api_slug=api,
        )
        if result.output_path:
            self._last_output_path = result.output_path
            self._queue.put(("__OUTPUT__:" + result.output_path, "success"))
            if result.upload_status == UploadStatus.SUCCESS:
                self._notifier.upload_success(
                    dataset_name="",
                    added_count=int(result.extracted_count or 0),
                )
            elif result.upload_status == UploadStatus.FAILED:
                self._notifier.upload_failed(result.error_message or "آپلود ناموفق")
        elif result.extraction_status == JobStatus.CANCELLED:
            pass
        elif result.extraction_status in (JobStatus.FAILED, JobStatus.NO_RESULTS):
            if result.error_message:
                self._last_scrape_error = result.error_message

    def _start(self) -> None:
        if not self._require_valid_license():
            return
        if not self._require_idle_execution("استخراج تکی"):
            return
        if self._scheduler.is_running:
            messagebox.showwarning("تداخل", "زمان‌بندی خودکار فعال است. ابتدا آن را متوقف کنید.")
            return
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("در حال اجرا", "فرآیند در حال اجراست.")
            return
        if not self.city_cb.get():
            messagebox.showwarning("هشدار", "لطفاً شهر را انتخاب کنید.")
            return
        if not self._execution.try_start(ExecutionState.RUNNING_SINGLE):
            messagebox.showinfo("در حال اجرا", "عملیات دیگری در حال اجراست.")
            return

        self._save_extraction_settings()
        self._reset_run_tracking(scheduled=False)
        self._cancel_event.clear()
        self.progress.set(0)
        self.progress_percent.configure(text="۰٪")
        self._reset_stat_cards()
        self.scrape_start_time = time.time()
        self._append_log("شروع استخراج...", "info")
        self._set_extraction_ui_running(batch=False)
        self._set_status_message("استخراج آگهی‌ها…", tone="running")
        if hasattr(self, "current_task_lbl"):
            self.current_task_lbl.configure(text="استخراج آگهی‌ها…")

        settings = self._collect_settings()
        self._last_run_settings = dict(settings)
        self._notifier.extraction_started(
            city=str(settings.get("city") or ""),
            transaction=str(settings.get("transaction_type") or ""),
            max_items=int(settings.get("max_items") or 0),
            scheduled=False,
        )
        self._worker = threading.Thread(
            target=self._run_scrape_thread, args=(settings,), daemon=True
        )
        self._worker.start()

    def _run_scrape_thread(self, settings: Dict[str, Any]) -> None:
        try:
            self._run_single_job(settings)
        except Exception as exc:
            self._emit_threadsafe(f"✗ خطا: {exc}", "error")
            self._storage.append_log(f"SCRAPE ERR: {exc}")
        finally:
            self._queue.put(("__DONE__", "normal"))

    def _cancel(self) -> None:
        if not self._execution.is_running:
            return
        self._run_cancelled = True
        self._execution.request_cancel()
        self._cancel_event.set()
        self._emit("درخواست لغو ارسال شد...", "warning")
        self._sync_tray_status()

    # ── Log / queue ─────────────────────────────────────────────────────
    def _emit_threadsafe(self, text: str, log_type: str = "normal") -> None:
        self._queue.put((text, log_type))

    def _progress_threadsafe(self, frac: float) -> None:
        if self._execution.state == ExecutionState.RUNNING_BATCH and self._batch_job_total > 0:
            combined = (self._batch_job_index + max(0.0, min(1.0, frac))) / self._batch_job_total
            self._queue.put((f"__PROGRESS__:{combined}", "normal"))
        else:
            self._queue.put((f"__PROGRESS__:{frac}", "normal"))

    def _emit(self, text: str, log_type: str = "normal") -> None:
        self._queue.put((text, log_type))

    def _append_log(self, text: str, log_type: str = "normal") -> None:
        from datetime import datetime
        ts = fa_digits(datetime.now().strftime("%H:%M:%S"))
        level = log_type if log_type in LOG_LEVEL_BADGES else "normal"
        badge = LOG_LEVEL_BADGES[level]
        self.log_box.configure(state="normal")
        tb = self.log_box._textbox
        tb.insert("end", f"[{ts}] ", "ts")
        tb.insert("end", f" {badge} ", level)
        tb.insert("end", f"\u200F{text}\n", "msg")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        if hasattr(self, "current_task_lbl"):
            self.current_task_lbl.configure(text=text[:90])

    def _poll_queue(self) -> None:
        try:
            while True:
                fn = self._ui_callbacks.get_nowait()
                try:
                    fn()
                except Exception:
                    pass
        except queue.Empty:
            pass
        try:
            while True:
                item = self._queue.get_nowait()
                if isinstance(item, tuple):
                    msg, log_type = item
                else:
                    msg, log_type = item, "normal"

                if msg.startswith("__PROGRESS__:"):
                    try:
                        frac = float(msg.split(":", 1)[1])
                        self.progress.set(max(0.0, min(1.0, frac)))
                        pct = int(frac * 100)
                        self.progress_percent.configure(text=f"{fa_digits(pct)}٪")
                        if self.scrape_start_time and frac > 0.02:
                            elapsed = time.time() - self.scrape_start_time
                            eta = elapsed * (1.0 - frac) / frac
                            em, es = divmod(int(eta), 60)
                            self.scrape_time_info.configure(
                                text=f"زمان باقی‌مانده تقریبی: {fa_digits(em)}:{fa_digits(f'{es:02d}')}"
                            )
                    except Exception:
                        pass
                elif msg.startswith("__BATCH_PROGRESS__:"):
                    try:
                        payload = msg.split(":", 1)[1]
                        index_s, total_s, frac_s, label = payload.split("|", 3)
                        index = int(index_s)
                        total = int(total_s)
                        frac = float(frac_s)
                        self._batch_job_index = index
                        self._batch_job_total = total
                        combined = (index + max(0.0, min(1.0, frac))) / max(1, total)
                        self.progress.set(max(0.0, min(1.0, combined)))
                        pct = int(combined * 100)
                        self.progress_percent.configure(text=f"{fa_digits(pct)}٪")
                        task = f"{fa_digits(index + 1)} از {fa_digits(total)} — {label}"
                        if hasattr(self, "current_task_lbl"):
                            self.current_task_lbl.configure(text=task)
                        if hasattr(self, "_workspace"):
                            self._workspace.timeline.set_running(index, label)
                            self._workspace.set_batch_overall(index, total, frac)
                        if hasattr(self, "_summary_card_subs"):
                            self._summary_card_subs.set_value(label[:40])
                        elif hasattr(self, "_chip_category") and hasattr(self._chip_category, "set_value"):
                            self._chip_category.set_value(label[:40])
                        elif hasattr(self, "_chip_category") and hasattr(self._chip_category, "set_text"):
                            self._chip_category.set_text(f"دسته: {label[:40]}")
                    except Exception:
                        pass
                elif msg.startswith("__BATCH_JOB_DONE__:"):
                    try:
                        result = BatchJobResult.from_dict(json.loads(msg.split(":", 1)[1]))
                        if hasattr(self, "_workspace"):
                            self._workspace.timeline.apply_job_result(result)
                    except Exception:
                        pass
                elif msg == "__BATCH_DONE__":
                    summary = self._batch_summary
                    if summary:
                        ok = summary.success_count
                        fail = summary.failed_count
                        self._append_log(
                            f"پایان batch — ✓ {fa_digits(ok)} موفق | ⚠ {fa_digits(fail)} نیازمند توجه",
                            "success" if fail == 0 else "warning",
                        )
                        try:
                            self._notifier.batch_complete(
                                success_count=ok,
                                failed_count=fail,
                                cancelled=bool(getattr(summary, "cancelled", False)),
                                total_jobs=int(getattr(summary, "total_jobs", 0) or (ok + fail)),
                            )
                        except Exception:
                            pass
                        if self._run_is_scheduled:
                            try:
                                self._record_scheduler_batch_run(summary)
                            except Exception as exc:
                                self._storage.append_log(f"SCHEDULER HISTORY ERR: {exc}")
                        if hasattr(self, "_workspace"):
                            try:
                                self._workspace.show_completed(summary)
                            except Exception:
                                pass
                        else:
                            self.after(
                                300,
                                lambda s=summary: BatchReportDialog(
                                    self,
                                    s,
                                    on_retry_failed=lambda jobs: self._retry_failed_batch_jobs(jobs),
                                ),
                            )
                    self._sync_tray_status()
                elif msg.startswith("__STATS__:"):
                    try:
                        stats = json.loads(msg.split(":", 1)[1])
                        self._last_run_stats = {
                            "total": int(stats.get("total_posts") or stats.get("total") or 0),
                            "done": int(stats.get("done") or 0),
                            "ok": int(stats.get("ok") or 0),
                        }
                        self._update_stat_cards(
                            total=self._last_run_stats["total"],
                            done=self._last_run_stats["done"],
                            ok=self._last_run_stats["ok"],
                        )
                    except Exception:
                        pass
                elif msg.startswith("__OUTPUT__:"):
                    path = msg.split(":", 1)[1]
                    self._run_had_output = True
                    self._pending_output_path = path
                    self._update_output_file_display(path)
                    self._sync_status_path(path)
                    self._emit(f"✓ اتمام — {path}", "success")
                elif msg == "__DONE__":
                    was_batch = self._active_batch_run
                    was_scheduled = bool(self._run_is_scheduled)
                    self._active_batch_run = False
                    self._execution.finish()
                    # اول تاریخچه/نوتیف — تا خطای UI مانع ثبت نشود
                    if not was_batch:
                        try:
                            self._notify_extraction_complete()
                        except Exception as exc:
                            self._storage.append_log(f"NOTIFY/HISTORY ERR: {exc}")
                    if hasattr(self, "_scheduler") and self._scheduler.is_running:
                        try:
                            self._scheduler.on_extraction_finished()
                        except Exception:
                            pass
                    try:
                        self._set_extraction_ui_idle()
                        self._set_status_message("آماده", tone="success")
                        if self.scrape_start_time:
                            elapsed = time.time() - self.scrape_start_time
                            mins, secs = divmod(int(elapsed), 60)
                            self.scrape_time_info.configure(
                                text=f"مدت کل: {fa_digits(mins)}:{fa_digits(f'{secs:02d}')}"
                            )
                            if hasattr(self, "current_task_lbl") and not was_batch:
                                self.current_task_lbl.configure(text="استخراج با موفقیت پایان یافت")
                        if hasattr(self, "_workspace") and not was_batch:
                            self._workspace.show_completed(single_ok=not self._run_cancelled)
                    except Exception as exc:
                        self._storage.append_log(f"DONE UI ERR: {exc}")
                    self._sync_tray_status()
                    if was_scheduled:
                        self.after(80, self._refresh_scheduler_live_banner)
                else:
                    self._append_log(msg, log_type)
                    if log_type == "error":
                        clean = msg.lstrip("✗ ").strip()
                        if clean:
                            self._last_scrape_error = clean
                    tone = log_type if log_type in ("success", "warning", "error", "info") else "muted"
                    if log_type == "info":
                        tone = "brand"
                    self._set_status_message(msg[:96], tone=tone)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ── Output helpers ──────────────────────────────────────────────────
    def _open_output_folder(self) -> None:
        path = get_output_dir()
        os.makedirs(path, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)

    def _open_platform(self) -> None:
        webbrowser.open(f"{SITE_URL}/workspace/datasets/")

    def _open_site(self) -> None:
        webbrowser.open(SITE_URL)

    def _open_buy_license(self) -> None:
        webbrowser.open(DEFAULT_BUY_LICENSE_URL)

    def _open_telegram(self) -> None:
        webbrowser.open(CREATOR_TELEGRAM_URL)

    def _copy_creator_phone(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(CREATOR_PHONE)
            self._set_status_message("شماره تماس کپی شد", tone="success")
        except Exception:
            messagebox.showinfo("تماس", CREATOR_PHONE_DISPLAY)


def run_app() -> None:
    app = ExtractorApp()
    app.mainloop()
