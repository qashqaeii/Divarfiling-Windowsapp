"""تنظیمات System Tray و اجرای پس‌زمینه."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


def default_tray_settings() -> Dict[str, Any]:
    return {
        "close_to_tray": True,
        "show_close_hint": True,
        "notify_extraction_complete": True,
        "notify_errors": True,
    }


@dataclass(frozen=True)
class TrayPrefs:
    close_to_tray: bool = True
    show_close_hint: bool = True
    notify_extraction_complete: bool = True
    notify_errors: bool = True


def parse_tray_prefs(settings: Dict[str, Any]) -> TrayPrefs:
    raw = settings.get("tray") or {}
    if not isinstance(raw, dict):
        raw = {}
    defaults = default_tray_settings()

    # سازگاری با کلیدهای قدیمی notifications در صورت نبود tray
    notify = settings.get("notifications") or {}
    if not isinstance(notify, dict):
        notify = {}

    return TrayPrefs(
        close_to_tray=bool(raw.get("close_to_tray", defaults["close_to_tray"])),
        show_close_hint=bool(raw.get("show_close_hint", defaults["show_close_hint"])),
        notify_extraction_complete=bool(
            raw.get(
                "notify_extraction_complete",
                notify.get("extraction", defaults["notify_extraction_complete"]),
            )
        ),
        notify_errors=bool(
            raw.get(
                "notify_errors",
                notify.get("errors", defaults["notify_errors"]),
            )
        ),
    )


def sync_tray_into_notifications(settings: Dict[str, Any]) -> Dict[str, Any]:
    """هم‌تراز کردن ترجیحات اعلان Tray با بخش notifications."""
    tray = parse_tray_prefs(settings)
    notifications = dict(settings.get("notifications") or {})
    notifications["extraction"] = tray.notify_extraction_complete
    notifications["errors"] = tray.notify_errors
    settings["notifications"] = notifications
    settings["tray"] = {
        "close_to_tray": tray.close_to_tray,
        "show_close_hint": tray.show_close_hint,
        "notify_extraction_complete": tray.notify_extraction_complete,
        "notify_errors": tray.notify_errors,
    }
    return settings
