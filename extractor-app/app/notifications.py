"""اعلان‌های بومی ویندوز — Toast با لوگو و fallback درون‌برنامه‌ای."""
from __future__ import annotations

import os
import sys
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from app.brand import ICON_ICO_ASSET, SITE_DISPLAY_NAME, get_logo_path
from app.formatters import fa_digits
from app.paths import get_resource_path

APP_USER_MODEL_ID = "IR.DivarFiling.Extractor"

_WINOTIFY_AVAILABLE = False
try:
    from winotify import Notification, audio as win_audio

    _WINOTIFY_AVAILABLE = True
except ImportError:
    Notification = None  # type: ignore[misc, assignment]
    win_audio = None  # type: ignore[misc, assignment]

_AUMID_REGISTERED = False
_ICON_PATH: Optional[str] = None


def default_notification_settings() -> Dict[str, Any]:
    return {
        "enabled": True,
        "sound": True,
        "when_minimized_only": False,
        "extraction": True,
        "scheduler": True,
        "license": True,
        "errors": True,
        "upload": True,
    }


@dataclass(frozen=True)
class NotificationPrefs:
    enabled: bool = True
    sound: bool = True
    when_minimized_only: bool = False
    extraction: bool = True
    scheduler: bool = True
    license: bool = True
    errors: bool = True
    upload: bool = True


def parse_notification_prefs(settings: Dict[str, Any]) -> NotificationPrefs:
    raw = settings.get("notifications") or {}
    if not isinstance(raw, dict):
        raw = {}
    defaults = default_notification_settings()
    return NotificationPrefs(
        enabled=bool(raw.get("enabled", defaults["enabled"])),
        sound=bool(raw.get("sound", defaults["sound"])),
        when_minimized_only=bool(raw.get("when_minimized_only", defaults["when_minimized_only"])),
        extraction=bool(raw.get("extraction", defaults["extraction"])),
        scheduler=bool(raw.get("scheduler", defaults["scheduler"])),
        license=bool(raw.get("license", defaults["license"])),
        errors=bool(raw.get("errors", defaults["errors"])),
        upload=bool(raw.get("upload", defaults["upload"])),
    )


def is_windows_notifications_supported() -> bool:
    return sys.platform == "win32"


def _register_aumid() -> None:
    global _AUMID_REGISTERED
    if _AUMID_REGISTERED or sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        _AUMID_REGISTERED = True
    except Exception:
        pass


def _resolve_icon_path() -> str:
    global _ICON_PATH
    if _ICON_PATH and os.path.isfile(_ICON_PATH):
        return _ICON_PATH
    for candidate in (
        get_resource_path(ICON_ICO_ASSET),
        get_logo_path(),
        get_resource_path("assets/icon.png"),
    ):
        if candidate and os.path.isfile(candidate):
            _ICON_PATH = os.path.abspath(candidate)
            return _ICON_PATH
    return ""


def _clip_text(text: str, limit: int = 240) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class WindowsNotificationService:
    """ارسال Toast ویندوز با تنظیمات کاربر و fallback."""

    def __init__(
        self,
        *,
        get_settings: Callable[[], Dict[str, Any]],
        is_app_minimized: Callable[[], bool],
        fallback_toast: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._get_settings = get_settings
        self._is_app_minimized = is_app_minimized
        self._fallback_toast = fallback_toast
        _register_aumid()

    @property
    def supported(self) -> bool:
        return is_windows_notifications_supported()

    def _prefs(self) -> NotificationPrefs:
        return parse_notification_prefs(self._get_settings())

    def _should_deliver(self, *, category: str, force: bool = False) -> bool:
        prefs = self._prefs()
        if not prefs.enabled or sys.platform != "win32":
            return False
        if not force and prefs.when_minimized_only and not self._is_app_minimized():
            return False
        category_map = {
            "extraction": prefs.extraction,
            "scheduler": prefs.scheduler,
            "license": prefs.license,
            "error": prefs.errors,
            "upload": prefs.upload,
            "test": True,
        }
        return bool(category_map.get(category, True))

    def _emit_fallback(self, message: str, tone: str) -> None:
        if self._fallback_toast:
            try:
                self._fallback_toast(message, tone)
            except Exception:
                pass

    def _show(
        self,
        *,
        title: str,
        message: str,
        category: str,
        tone: str = "info",
        duration: str = "short",
        force: bool = False,
        launch_path: str = "",
    ) -> bool:
        if not self._should_deliver(category=category, force=force):
            return False

        title = _clip_text(title, 64)
        message = _clip_text(message, 240)
        prefs = self._prefs()

        if not _WINOTIFY_AVAILABLE:
            self._emit_fallback(f"{title}\n{message}", tone)
            return False

        icon = _resolve_icon_path()

        def _worker() -> None:
            try:
                toast = Notification(
                    app_id=APP_USER_MODEL_ID,
                    title=title,
                    msg=message,
                    icon=icon,
                    duration=duration,
                )
                if launch_path and os.path.exists(launch_path):
                    try:
                        toast.add_actions(label="باز کردن", launch=os.path.abspath(launch_path))
                    except Exception:
                        pass
                if prefs.sound and win_audio is not None:
                    toast.set_audio(win_audio.Default, loop=False)
                elif win_audio is not None:
                    toast.set_audio(win_audio.Silent, loop=False)
                toast.show()
            except Exception:
                self._emit_fallback(f"{title}\n{message}", tone)

        threading.Thread(target=_worker, daemon=True).start()
        return True

    # ── عمومی ───────────────────────────────────────────────────────────

    def test(self) -> bool:
        return self._show(
            title=f"{SITE_DISPLAY_NAME}",
            message="اعلان‌های ویندوز فعال است — همه چیز آماده است.",
            category="test",
            tone="success",
            force=True,
        )

    # ── استخراج ─────────────────────────────────────────────────────────

    def extraction_started(
        self,
        *,
        city: str = "",
        transaction: str = "",
        max_items: int = 0,
        scheduled: bool = False,
    ) -> bool:
        source = "زمان‌بندی خودکار" if scheduled else "استخراج دستی"
        parts = [source]
        if city:
            parts.append(city)
        if transaction:
            parts.append(transaction)
        if max_items > 0:
            parts.append(f"حداکثر {fa_digits(max_items)} آگهی")
        return self._show(
            title="شروع استخراج",
            message=" · ".join(parts),
            category="extraction",
            tone="info",
            duration="short",
        )

    def extraction_success(
        self,
        *,
        output_path: str = "",
        city: str = "",
        ok_count: int = 0,
        total_count: int = 0,
        duration_text: str = "",
        scheduled: bool = False,
    ) -> bool:
        headline = "استخراج زمان‌بندی‌شده تمام شد" if scheduled else "استخراج با موفقیت انجام شد"
        lines = []
        if ok_count or total_count:
            lines.append(
                f"{fa_digits(ok_count or total_count)} آگهی"
                + (f" از {fa_digits(total_count)}" if total_count and ok_count != total_count else "")
            )
        if city:
            lines.append(city)
        if duration_text:
            lines.append(f"مدت: {duration_text}")
        if output_path:
            lines.append(os.path.basename(output_path))
        folder = os.path.dirname(output_path) if output_path else ""
        return self._show(
            title=headline,
            message="\n".join(lines) if lines else "فایل خروجی آماده است.",
            category="extraction",
            tone="success",
            duration="long",
            launch_path=folder,
        )

    def extraction_failed(
        self,
        reason: str,
        *,
        scheduled: bool = False,
    ) -> bool:
        title = "خطا در استخراج زمان‌بندی‌شده" if scheduled else "خطا در استخراج"
        return self._show(
            title=title,
            message=reason or "استخراج بدون نتیجه پایان یافت.",
            category="error",
            tone="error",
            duration="long",
            force=True,
        )

    def extraction_cancelled(self, *, scheduled: bool = False) -> bool:
        title = "لغو استخراج زمان‌بندی‌شده" if scheduled else "استخراج لغو شد"
        return self._show(
            title=title,
            message="فرآیند توسط کاربر متوقف شد.",
            category="extraction",
            tone="warning",
        )

    def extraction_no_results(self, *, scheduled: bool = False) -> bool:
        title = "بدون نتیجه"
        msg = (
            "زمان‌بندی: هیچ آگهی‌ای یافت نشد."
            if scheduled
            else "هیچ آگهی‌ای در محدوده انتخاب‌شده یافت نشد."
        )
        return self._show(
            title=title,
            message=msg,
            category="extraction",
            tone="warning",
            duration="long",
        )

    def batch_complete(
        self,
        *,
        success_count: int = 0,
        failed_count: int = 0,
        cancelled: bool = False,
        total_jobs: int = 0,
    ) -> bool:
        if cancelled:
            title = "استخراج گروهی متوقف شد"
            tone = "warning"
        elif failed_count:
            title = "پایان استخراج گروهی با هشدار"
            tone = "warning"
        else:
            title = "پایان استخراج گروهی"
            tone = "success"
        parts = []
        if total_jobs:
            parts.append(f"{fa_digits(total_jobs)} زیردسته")
        if success_count:
            parts.append(f"{fa_digits(success_count)} موفق")
        if failed_count:
            parts.append(f"{fa_digits(failed_count)} نیازمند توجه")
        return self._show(
            title=title,
            message=" · ".join(parts) if parts else "عملیات گروهی به پایان رسید.",
            category="extraction",
            tone=tone,
            duration="long",
        )

    def background_mode_active(self) -> bool:
        return self._show(
            title="اجرا در پس‌زمینه",
            message="برنامه در System Tray فعال است. استخراج و زمان‌بندی ادامه دارند.",
            category="extraction",
            tone="info",
            duration="short",
        )

    def status_info(self, *, title: str, message: str) -> bool:
        return self._show(
            title=title,
            message=message,
            category="extraction",
            tone="info",
            duration="short",
            force=True,
        )

    # ── زمان‌بندی ───────────────────────────────────────────────────────

    def scheduler_started(self, *, interval_label: str = "", city: str = "", max_items: int = 0) -> bool:
        parts = ["زمان‌بندی خودکار فعال شد"]
        if interval_label:
            parts.append(interval_label)
        if city:
            parts.append(city)
        if max_items >= 0:
            parts.append(f"هر بار {fa_digits(max_items)} آگهی")
        return self._show(
            title="زمان‌بندی فعال",
            message=" · ".join(parts[1:]) if len(parts) > 1 else parts[0],
            category="scheduler",
            tone="success",
        )

    def scheduler_stopped(self) -> bool:
        return self._show(
            title="زمان‌بندی متوقف شد",
            message="اجرای خودکار استخراج غیرفعال شد.",
            category="scheduler",
            tone="info",
        )

    def scheduler_next_run(self, *, when_text: str = "") -> bool:
        return self._show(
            title="اجرای بعدی زمان‌بندی",
            message=when_text or "استخراج بعدی برنامه‌ریزی شد.",
            category="scheduler",
            tone="info",
            duration="short",
        )

    # ── لایسنس ──────────────────────────────────────────────────────────

    def license_activated(self, *, plan_name: str = "") -> bool:
        msg = f"پلن «{plan_name}»" if plan_name else "دسترسی کامل به استخراج فعال است."
        return self._show(
            title="لایسنس فعال شد",
            message=msg,
            category="license",
            tone="success",
        )

    def license_deactivated(self) -> bool:
        return self._show(
            title="لایسنس غیرفعال شد",
            message="برای ادامه استفاده، لایسنس را مجدداً فعال کنید.",
            category="license",
            tone="warning",
        )

    def license_invalid(self, reason: str = "") -> bool:
        return self._show(
            title="لایسنس نامعتبر",
            message=reason or "لطفاً لایسنس را بررسی یا تمدید کنید.",
            category="license",
            tone="error",
            duration="long",
            force=True,
        )

    def license_expiring_soon(self, *, days_left: int) -> bool:
        return self._show(
            title="یادآوری انقضای لایسنس",
            message=f"{fa_digits(days_left)} روز تا پایان اعتبار باقی مانده است.",
            category="license",
            tone="warning",
            duration="long",
        )

    # ── آپلود پلتفرم ────────────────────────────────────────────────────

    def upload_success(self, *, dataset_name: str = "", added_count: int = 0) -> bool:
        parts = ["فایل در پلتفرم ثبت شد"]
        if dataset_name:
            parts.append(f"مجموعه: {dataset_name}")
        if added_count:
            parts.append(f"{fa_digits(added_count)} آگهی جدید")
        return self._show(
            title="آپلود موفق",
            message=" · ".join(parts[1:]) if len(parts) > 1 else parts[0],
            category="upload",
            tone="success",
        )

    def upload_failed(self, reason: str = "") -> bool:
        return self._show(
            title="خطا در آپلود پلتفرم",
            message=reason or "ارسال فایل به سرور ناموفق بود.",
            category="upload",
            tone="error",
            duration="long",
            force=True,
        )
